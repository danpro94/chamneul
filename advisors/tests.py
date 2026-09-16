"""Tests for the advisor-application API (M4-4, api.md #11-#15).

M4-4 was implemented before the test-first decision (D-7, 2026-09-09), so this
file starts from the regression that prompted it: the 2026-09-14 audit of
SPEC-002's M-1 finding turned up the same read-check-write shape here
(finding A-1). Broader #11-#15 coverage remains outstanding debt.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts import services as accounts_services
from accounts.models import Role, RoleGrant, UserRole
from common.exceptions import Conflict
from common.taxonomy import ConcernType
from notifications.models import Notification

from . import services
from .models import (
    AdvisorApplication,
    AdvisorApplicationStatus,
    CurrentStatus,
    DomainCategory,
    ExperienceBand,
    IntendedLane,
)

User = get_user_model()


def admin_application_url(application_id):
    return f"/api/v1/admin/advisor-applications/{application_id}"


class AdvisorApplicationReviewTests(TestCase):
    """api.md #15 — review transitions and their side effects."""

    def setUp(self):
        self.client = APIClient()
        self.applicant = User.objects.create_user(
            email="applicant@example.com", nickname="applicant", password="pw12345!"
        )
        self.admin = User.objects.create_user(
            email="reviewadmin@example.com", nickname="reviewadmin", password="pw12345!"
        )
        UserRole.objects.create(user=self.admin, role=Role.ADMIN)
        self.application = self.make_application()

    def make_application(self, **kwargs):
        return AdvisorApplication.objects.create(
            applicant=kwargs.pop("applicant", self.applicant),
            display_name=kwargs.pop("display_name", "심사대상자"),
            domain_category=DomainCategory.HR_ORG,
            experience_band=ExperienceBand.BAND_5_7,
            current_status=CurrentStatus.EMPLOYED,
            intended_lane=IntendedLane.EXPERT,
            career_narrative="경력 서술",
            advisable_concern_types=[ConcernType.BURNOUT],
            sample_advice_response="샘플 답변",
            status=kwargs.pop("status", AdvisorApplicationStatus.REVIEWING),
            **kwargs,
        )

    # --- A-1: the service must not trust a caller-supplied snapshot -------

    def test_review_rejects_transition_decided_after_the_caller_read_it(self):
        """The 2026-09-14 audit's A-1.

        The view used to fetch the application and hand the *object* to the
        service, which then checked the transition against that unlocked
        snapshot. Two admins clicking approve at once both passed the check
        and both ran the side effects — two RoleGrant audit rows and two
        notifications for one approval, corrupting the very trail ADR-003 §3
        exists to keep. The service now re-reads under a row lock, so a
        decision already committed elsewhere is a 409.
        """
        # Another admin's approval lands after this caller read the row.
        AdvisorApplication.objects.filter(pk=self.application.pk).update(
            status=AdvisorApplicationStatus.APPROVED
        )

        with self.assertRaises(Conflict):
            services.review_application(
                self.application.pk,
                actor=self.admin,
                target_status=AdvisorApplicationStatus.APPROVED,
            )

        self.assertFalse(RoleGrant.objects.exists())
        self.assertFalse(Notification.objects.exists())

    def test_second_approval_through_the_api_is_409_with_no_duplicate_audit(self):
        self.client.force_authenticate(self.admin)
        payload = {"status": AdvisorApplicationStatus.APPROVED}

        first = self.client.patch(
            admin_application_url(self.application.id), payload, format="json"
        )
        second = self.client.patch(
            admin_application_url(self.application.id), payload, format="json"
        )

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(RoleGrant.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 1)

    # --- baseline coverage for the transitions themselves -----------------

    def test_approval_grants_role_writes_audit_and_notifies(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            admin_application_url(self.application.id),
            {"status": AdvisorApplicationStatus.APPROVED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            UserRole.objects.filter(user=self.applicant, role=Role.ADVISOR).exists()
        )
        self.assertEqual(RoleGrant.objects.filter(user=self.applicant).count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.applicant).count(), 1)

    def test_rejection_without_reason_is_422(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            admin_application_url(self.application.id),
            {"status": AdvisorApplicationStatus.REJECTED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(Notification.objects.exists())

    def test_rejection_stores_reason_and_notifies_applicant(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            admin_application_url(self.application.id),
            {"status": AdvisorApplicationStatus.REJECTED, "reject_reason": "경력 불충분"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.application.refresh_from_db()
        self.assertEqual(self.application.reject_reason, "경력 불충분")
        self.assertFalse(
            UserRole.objects.filter(user=self.applicant, role=Role.ADVISOR).exists()
        )
        self.assertEqual(Notification.objects.filter(recipient=self.applicant).count(), 1)

    def test_review_requires_admin(self):
        self.client.force_authenticate(self.applicant)
        response = self.client.patch(
            admin_application_url(self.application.id),
            {"status": AdvisorApplicationStatus.APPROVED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_review_of_missing_application_is_404(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            admin_application_url("00000000-0000-7000-8000-000000000000"),
            {"status": AdvisorApplicationStatus.APPROVED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ReapplyAfterRevokeTests(TestCase):
    """회수된 조언가의 재신청 (Owner 결정 2026-09-16, 리뷰 AR-01).

    #43이 생기기 전에는 ADVISOR 역할을 잃을 방법이 없었으므로 "한 번 승인되면
    영원히 APPROVED"가 무해했다. 회수가 가능해진 순간 그 상태는 막다른 길이
    된다 — Phase 2에는 사용자측 신청 취소 API가 없어서(CLAUDE.md §5) 관리자가
    #42로 역할을 다시 주는 것 외에 빠져나올 방법이 없었다.
    """

    def setUp(self):
        self.admin = User.objects.create_user(
            email="reapply.admin@example.com", nickname="reapplyadmin", password="pw12345!"
        )
        UserRole.objects.create(user=self.admin, role=Role.ADMIN)
        self.applicant = User.objects.create_user(
            email="reapply@example.com", nickname="reapply", password="pw12345!"
        )

    def payload(self, display_name):
        return {
            "display_name": display_name,
            "domain_category": DomainCategory.HR_ORG,
            "experience_band": ExperienceBand.BAND_5_7,
            "current_status": CurrentStatus.EMPLOYED,
            "intended_lane": IntendedLane.EXPERT,
            "career_narrative": "경력 서술",
            "advisable_concern_types": [ConcernType.BURNOUT],
            "sample_advice_response": "샘플 답변",
        }

    def approve_and_revoke(self):
        application = services.create_application(
            self.applicant, self.payload("최초 신청")
        )
        AdvisorApplication.objects.filter(pk=application.pk).update(
            status=AdvisorApplicationStatus.REVIEWING
        )
        services.review_application(
            application.pk,
            actor=self.admin,
            target_status=AdvisorApplicationStatus.APPROVED,
        )
        accounts_services.revoke_role(
            self.applicant.id, role=Role.ADVISOR, actor=self.admin
        )

    def test_approved_application_blocks_reapply_while_the_role_is_held(self):
        """대조군 — 역할을 보유한 동안에는 재신청이 여전히 막힌다."""
        application = services.create_application(
            self.applicant, self.payload("최초 신청")
        )
        AdvisorApplication.objects.filter(pk=application.pk).update(
            status=AdvisorApplicationStatus.REVIEWING
        )
        services.review_application(
            application.pk,
            actor=self.admin,
            target_status=AdvisorApplicationStatus.APPROVED,
        )

        with self.assertRaises(Conflict):
            services.create_application(self.applicant, self.payload("중복 신청"))

    def test_can_reapply_after_the_advisor_role_is_revoked(self):
        self.approve_and_revoke()

        reapplied = services.create_application(self.applicant, self.payload("재신청"))

        self.assertEqual(reapplied.status, AdvisorApplicationStatus.PENDING)
        self.assertEqual(
            AdvisorApplication.objects.filter(applicant=self.applicant).count(), 2
        )

    def test_pending_application_still_blocks_a_second_one_after_revoke(self):
        """회수가 '무제한 신청'을 열어주는 것은 아니다 — 새로 낸 신청이
        진행 중이면 그다음은 여전히 409."""
        self.approve_and_revoke()
        services.create_application(self.applicant, self.payload("재신청"))

        with self.assertRaises(Conflict):
            services.create_application(self.applicant, self.payload("세 번째"))
