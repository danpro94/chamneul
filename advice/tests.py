"""Tests for advice + feedback API (SPEC-002, api.md #26-#38).

Written before the code they exercise exists (specs/SPEC-002-advice-api/
tasks.md — TDD: each test class must fail first, then pass after
implementation).

The fixture every class needs is the same (concern owner / assigned advisor /
unassigned advisor / admin / a concern with an active assignment), so it lives
once in AdviceTestBase — SPEC-001 duplicated its setUp five times.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import ActiveRole, Role, UserRole
from advisors.models import (
    AdvisorApplication,
    AdvisorApplicationStatus,
    CurrentStatus,
    DomainCategory,
    ExperienceBand,
    IntendedLane,
)
from common.taxonomy import ConcernType
from concerns.models import Assignment, Concern, ConcernStatus, TriageDecision
from notifications.models import Notification, NotificationType

from .models import Advice, AdviceHistory, AdviceStatus, Feedback, FeedbackStatus

User = get_user_model()

ADVICES_WRITTEN_URL = "/api/v1/users/me/advices-written"
ADMIN_ADVICES_URL = "/api/v1/admin/advices"
RECEIVED_ADVICES_URL = "/api/v1/users/me/advices"
MY_FEEDBACKS_URL = "/api/v1/users/me/feedbacks"
ADMIN_FEEDBACKS_URL = "/api/v1/admin/feedbacks"


def feedbacks_url(advice_id):
    return f"/api/v1/advices/{advice_id}/feedbacks"


def admin_feedback_url(feedback_id):
    return f"/api/v1/admin/feedbacks/{feedback_id}"


def advice_detail_url(advice_id):
    return f"/api/v1/advices/{advice_id}"


def advice_review_url(advice_id):
    return f"/api/v1/admin/advices/{advice_id}/review"


class AdviceTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.requester = User.objects.create_user(
            email="requester@example.com", nickname="requester", password="pw12345!"
        )
        self.advisor = self.make_advisor("advisor1@example.com", "advisor1")
        self.other_advisor = self.make_advisor("advisor2@example.com", "advisor2")
        self.admin = User.objects.create_user(
            email="admin@example.com", nickname="admin", password="pw12345!"
        )
        UserRole.objects.create(user=self.admin, role=Role.ADMIN)

        self.concern = Concern.objects.create(
            author=self.requester,
            concern_summary="조언이 필요한 고민",
            concern_type=ConcernType.BURNOUT,
            status=ConcernStatus.ASSIGNED,
        )
        self.assignment = Assignment.objects.create(
            concern=self.concern,
            advisor=self.advisor,
            assigned_by=self.admin,
            triage_decision=TriageDecision.SUITABLE,
        )

    def make_advisor(self, email, nickname, active=True):
        """An ADVISOR-role user, switched into the role unless active=False."""
        user = User.objects.create_user(
            email=email, nickname=nickname, password="pw12345!"
        )
        UserRole.objects.create(user=user, role=Role.ADVISOR)
        if active:
            user.active_role = ActiveRole.ADVISOR
            user.save(update_fields=["active_role"])
        return user

    def make_advice(self, advisor=None, concern=None, **kwargs):
        return Advice.objects.create(
            concern=concern or self.concern,
            advisor=advisor or self.advisor,
            directional_guidance=kwargs.pop("directional_guidance", "기본 조언 본문"),
            **kwargs,
        )

    def advices_url(self, concern_id=None):
        return f"/api/v1/concerns/{concern_id or self.concern.id}/advices"

    def create_payload(self, **overrides):
        payload = {"directional_guidance": "이런 방향으로 생각해보시면 좋겠습니다."}
        payload.update(overrides)
        return payload


class AdviceCreateTests(AdviceTestBase):
    """SPEC-002 TASK-001 — api.md #28."""

    def test_create_requires_login(self):
        response = self.client.post(
            self.advices_url(), self.create_payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_active_advisor_role(self):
        # Holds ADVISOR but has not switched into it (api.md §2 Roles).
        passive = self.make_advisor("passive@example.com", "passive", active=False)
        Assignment.objects.create(
            concern=self.concern,
            advisor=passive,
            assigned_by=self.admin,
            triage_decision=TriageDecision.SUITABLE,
        )

        self.client.force_authenticate(passive)
        response = self.client.post(
            self.advices_url(), self.create_payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_rejects_unassigned_advisor(self):
        self.client.force_authenticate(self.other_advisor)
        response = self.client.post(
            self.advices_url(), self.create_payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_success_defaults_to_submitted(self):
        self.client.force_authenticate(self.advisor)
        response = self.client.post(
            self.advices_url(), self.create_payload(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], AdviceStatus.PENDING)
        self.assertEqual(response.data["version"], 1)
        self.assertEqual(response.data["concern_id"], str(self.concern.id))
        self.assertEqual(response.data["advisor_user_id"], str(self.advisor.id))

        advice = Advice.objects.get(pk=response.data["advice_id"])
        self.assertTrue(advice.is_submitted)

    def test_create_as_draft_keeps_is_submitted_false(self):
        # draft = PENDING + is_submitted=False (spec.md §4). It is a flag, not
        # a status — the admin review queue must filter on it (TASK-004).
        self.client.force_authenticate(self.advisor)
        response = self.client.post(
            self.advices_url(), self.create_payload(submit=False), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        advice = Advice.objects.get(pk=response.data["advice_id"])
        self.assertFalse(advice.is_submitted)
        self.assertEqual(advice.status, AdviceStatus.PENDING)

    def test_create_rejects_guidance_over_1500_chars(self):
        self.client.force_authenticate(self.advisor)
        response = self.client.post(
            self.advices_url(),
            self.create_payload(directional_guidance="가" * 1501),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_second_advice_for_same_concern_returns_409(self):
        self.make_advice()

        self.client.force_authenticate(self.advisor)
        response = self.client.post(
            self.advices_url(), self.create_payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_create_after_delete_is_allowed(self):
        # The partial unique excludes DELETED (model.md §3.8), so a withdrawn
        # advice must not block a rewrite.
        self.make_advice(status=AdviceStatus.DELETED)

        self.client.force_authenticate(self.advisor)
        response = self.client.post(
            self.advices_url(), self.create_payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_on_missing_concern_returns_404(self):
        self.client.force_authenticate(self.advisor)
        response = self.client.post(
            self.advices_url("00000000-0000-7000-8000-000000000000"),
            self.create_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_on_soft_deleted_concern_returns_404(self):
        from django.utils import timezone

        self.concern.deleted_at = timezone.now()
        self.concern.save(update_fields=["deleted_at"])

        self.client.force_authenticate(self.advisor)
        response = self.client.post(
            self.advices_url(), self.create_payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AdvicesWrittenTests(AdviceTestBase):
    """SPEC-002 TASK-001 — api.md #31."""

    def test_list_requires_login(self):
        response = self.client.get(ADVICES_WRITTEN_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_requires_active_advisor_role(self):
        self.client.force_authenticate(self.requester)
        response = self.client.get(ADVICES_WRITTEN_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_returns_own_advices_regardless_of_status(self):
        mine_pending = self.make_advice()
        other_concern = Concern.objects.create(
            author=self.requester,
            concern_summary="다른 고민",
            concern_type=ConcernType.JOB_CHANGE,
        )
        mine_rejected = self.make_advice(
            concern=other_concern, status=AdviceStatus.REJECTED
        )
        # Another advisor's advice must not appear.
        self.make_advice(advisor=self.other_advisor, concern=other_concern)

        self.client.force_authenticate(self.advisor)
        response = self.client.get(ADVICES_WRITTEN_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("page_info", response.data)
        ids = {item["advice_id"] for item in response.data["items"]}
        self.assertEqual(ids, {str(mine_pending.id), str(mine_rejected.id)})

    def test_list_exposes_is_submitted_and_version(self):
        advice = self.make_advice(is_submitted=False, version=3)

        self.client.force_authenticate(self.advisor)
        response = self.client.get(ADVICES_WRITTEN_URL)

        item = response.data["items"][0]
        self.assertEqual(item["advice_id"], str(advice.id))
        self.assertFalse(item["is_submitted"])
        self.assertEqual(item["version"], 3)

    def test_list_status_filter(self):
        self.make_advice()
        other_concern = Concern.objects.create(
            author=self.requester,
            concern_summary="다른 고민",
            concern_type=ConcernType.JOB_CHANGE,
        )
        approved = self.make_advice(
            concern=other_concern, status=AdviceStatus.APPROVED
        )

        self.client.force_authenticate(self.advisor)
        response = self.client.get(
            ADVICES_WRITTEN_URL, {"status": AdviceStatus.APPROVED}
        )

        ids = [item["advice_id"] for item in response.data["items"]]
        self.assertEqual(ids, [str(approved.id)])

    def test_list_concern_id_filter(self):
        target = self.make_advice()
        other_concern = Concern.objects.create(
            author=self.requester,
            concern_summary="다른 고민",
            concern_type=ConcernType.JOB_CHANGE,
        )
        self.make_advice(concern=other_concern)

        self.client.force_authenticate(self.advisor)
        response = self.client.get(
            ADVICES_WRITTEN_URL, {"concern_id": str(self.concern.id)}
        )

        ids = [item["advice_id"] for item in response.data["items"]]
        self.assertEqual(ids, [str(target.id)])

    def test_list_date_range_filter(self):
        advice = self.make_advice()
        created = advice.created_at.date().isoformat()

        self.client.force_authenticate(self.advisor)
        included = self.client.get(
            ADVICES_WRITTEN_URL, {"from_date": created, "to_date": created}
        )
        self.assertEqual(len(included.data["items"]), 1)

        excluded = self.client.get(ADVICES_WRITTEN_URL, {"from_date": "2099-01-01"})
        self.assertEqual(len(excluded.data["items"]), 0)

    def test_list_query_count_is_bounded(self):
        for index in range(5):
            concern = Concern.objects.create(
                author=self.requester,
                concern_summary=f"고민 {index}",
                concern_type=ConcernType.BURNOUT,
            )
            self.make_advice(concern=concern)

        self.client.force_authenticate(self.advisor)
        # COUNT for pagination + the page itself. Must not grow with N rows
        # (TEST_CRITERIA §3).
        with self.assertNumQueries(2):
            response = self.client.get(ADVICES_WRITTEN_URL)
        self.assertEqual(response.data["page_info"]["total"], 5)


class AdviceDetailTests(AdviceTestBase):
    """SPEC-002 TASK-002 — api.md #27, the three-audience visibility rule
    (spec.md §7-4, CLAUDE.md §6.2)."""

    def test_detail_requires_login(self):
        advice = self.make_advice()
        response = self.client.get(advice_detail_url(advice.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_detail_nonexistent_returns_404(self):
        self.client.force_authenticate(self.advisor)
        response = self.client.get(
            advice_detail_url("00000000-0000-7000-8000-000000000000")
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- author: any status, sees is_submitted + reject_reason -----------

    def test_detail_author_sees_rejected_with_reason(self):
        advice = self.make_advice(
            status=AdviceStatus.REJECTED, reject_reason="근거가 불충분합니다."
        )

        self.client.force_authenticate(self.advisor)
        response = self.client.get(advice_detail_url(advice.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], AdviceStatus.REJECTED)
        self.assertEqual(response.data["reject_reason"], "근거가 불충분합니다.")
        self.assertIn("is_submitted", response.data)
        self.assertEqual(response.data["advisor_display_name"], self.advisor.nickname)

    def test_detail_author_sees_own_draft(self):
        advice = self.make_advice(is_submitted=False)

        self.client.force_authenticate(self.advisor)
        response = self.client.get(advice_detail_url(advice.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_submitted"])

    # --- concern owner: APPROVED only, never reject_reason ----------------

    def test_detail_owner_sees_approved_without_reason(self):
        advice = self.make_advice(status=AdviceStatus.APPROVED)

        self.client.force_authenticate(self.requester)
        response = self.client.get(advice_detail_url(advice.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("reject_reason", response.data)

    def test_detail_owner_forbidden_for_pending(self):
        advice = self.make_advice(status=AdviceStatus.PENDING)

        self.client.force_authenticate(self.requester)
        response = self.client.get(advice_detail_url(advice.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_owner_forbidden_for_rejected(self):
        # Not just "not yet visible" — REJECTED never becomes visible to the
        # concern owner at all (§6.2: only APPROVED is ever shown to users).
        advice = self.make_advice(
            status=AdviceStatus.REJECTED, reject_reason="사유"
        )

        self.client.force_authenticate(self.requester)
        response = self.client.get(advice_detail_url(advice.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- admin: any status, sees reject_reason ----------------------------

    def test_detail_admin_sees_pending_with_reason_field(self):
        advice = self.make_advice(status=AdviceStatus.PENDING)

        self.client.force_authenticate(self.admin)
        response = self.client.get(advice_detail_url(advice.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("reject_reason", response.data)

    # --- everyone else: 403 ------------------------------------------------

    def test_detail_unrelated_advisor_forbidden(self):
        advice = self.make_advice(status=AdviceStatus.APPROVED)

        self.client.force_authenticate(self.other_advisor)
        response = self.client.get(advice_detail_url(advice.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_unrelated_user_forbidden(self):
        advice = self.make_advice(status=AdviceStatus.APPROVED)
        bystander = User.objects.create_user(
            email="bystander@example.com", nickname="bystander", password="pw12345!"
        )

        self.client.force_authenticate(bystander)
        response = self.client.get(advice_detail_url(advice.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_never_exposes_advisor_identity_beyond_display_name(self):
        advice = self.make_advice(status=AdviceStatus.APPROVED)

        self.client.force_authenticate(self.requester)
        response = self.client.get(advice_detail_url(advice.id))

        self.assertNotIn("advisor_user_id", response.data)
        self.assertNotIn("email", response.data)


class AdviceUpdateTests(AdviceTestBase):
    """SPEC-002 TASK-003 — api.md #29."""

    def test_update_requires_login(self):
        advice = self.make_advice()
        response = self.client.patch(
            advice_detail_url(advice.id),
            {"directional_guidance": "수정된 본문"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_requires_active_advisor_role(self):
        # Owns the advice, but hasn't switched into ADVISOR (api.md §2 Roles
        # — same gate as #28/#31).
        passive = self.make_advisor("passive2@example.com", "passive2", active=False)
        advice = self.make_advice(advisor=passive)

        self.client.force_authenticate(passive)
        response = self.client.patch(
            advice_detail_url(advice.id),
            {"directional_guidance": "수정된 본문"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_body_change_bumps_version_and_snapshots_previous_body(self):
        advice = self.make_advice(directional_guidance="원래 본문")

        self.client.force_authenticate(self.advisor)
        response = self.client.patch(
            advice_detail_url(advice.id),
            {"directional_guidance": "고친 본문"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["version"], 2)

        advice.refresh_from_db()
        self.assertEqual(advice.version, 2)
        self.assertEqual(advice.directional_guidance, "고친 본문")

        history = AdviceHistory.objects.get(advice=advice)
        self.assertEqual(history.version, 1)
        self.assertEqual(history.directional_guidance, "원래 본문")
        self.assertEqual(history.edited_by, self.advisor)

    def test_update_submit_only_does_not_bump_version_or_snapshot(self):
        # Owner decision 2026-09-11 (spec.md §7-2): version is the body-
        # history counter — toggling `submit` alone must not touch it.
        advice = self.make_advice(is_submitted=False)

        self.client.force_authenticate(self.advisor)
        response = self.client.patch(
            advice_detail_url(advice.id), {"submit": True}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["version"], 1)
        advice.refresh_from_db()
        self.assertTrue(advice.is_submitted)
        self.assertFalse(AdviceHistory.objects.filter(advice=advice).exists())

    def test_update_allowed_in_reviewing_state(self):
        advice = self.make_advice(status=AdviceStatus.REVIEWING)

        self.client.force_authenticate(self.advisor)
        response = self.client.patch(
            advice_detail_url(advice.id),
            {"directional_guidance": "심사중 수정"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_rejected_when_approved(self):
        advice = self.make_advice(status=AdviceStatus.APPROVED)

        self.client.force_authenticate(self.advisor)
        response = self.client.patch(
            advice_detail_url(advice.id),
            {"directional_guidance": "승인 후 수정 시도"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_update_rejected_when_deleted(self):
        advice = self.make_advice(status=AdviceStatus.DELETED)

        self.client.force_authenticate(self.advisor)
        response = self.client.patch(
            advice_detail_url(advice.id),
            {"directional_guidance": "삭제 후 수정 시도"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_update_forbidden_for_non_author(self):
        advice = self.make_advice()

        self.client.force_authenticate(self.other_advisor)
        response = self.client.patch(
            advice_detail_url(advice.id),
            {"directional_guidance": "남의 조언 수정 시도"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_nonexistent_advice_returns_404(self):
        self.client.force_authenticate(self.advisor)
        response = self.client.patch(
            advice_detail_url("00000000-0000-7000-8000-000000000000"),
            {"directional_guidance": "본문"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AdviceDeleteTests(AdviceTestBase):
    """SPEC-002 TASK-003 — api.md #30."""

    def test_delete_requires_login(self):
        advice = self.make_advice()
        response = self.client.delete(advice_detail_url(advice.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_pending_succeeds(self):
        advice = self.make_advice(status=AdviceStatus.PENDING)

        self.client.force_authenticate(self.advisor)
        response = self.client.delete(advice_detail_url(advice.id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        advice.refresh_from_db()
        self.assertEqual(advice.status, AdviceStatus.DELETED)

    def test_delete_reviewing_succeeds(self):
        advice = self.make_advice(status=AdviceStatus.REVIEWING)

        self.client.force_authenticate(self.advisor)
        response = self.client.delete(advice_detail_url(advice.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_approved_returns_409(self):
        advice = self.make_advice(status=AdviceStatus.APPROVED)

        self.client.force_authenticate(self.advisor)
        response = self.client.delete(advice_detail_url(advice.id))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_delete_already_deleted_returns_409(self):
        advice = self.make_advice(status=AdviceStatus.DELETED)

        self.client.force_authenticate(self.advisor)
        response = self.client.delete(advice_detail_url(advice.id))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_delete_forbidden_for_non_author(self):
        advice = self.make_advice()

        self.client.force_authenticate(self.other_advisor)
        response = self.client.delete(advice_detail_url(advice.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_nonexistent_returns_404(self):
        self.client.force_authenticate(self.advisor)
        response = self.client.delete(
            advice_detail_url("00000000-0000-7000-8000-000000000000")
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_then_recreate_is_allowed(self):
        # Ties back to AC-1: the (concern, advisor) partial unique excludes
        # DELETED, so a withdrawn advice must not block a rewrite — proven
        # here through the real DELETE endpoint, not a direct ORM write.
        advice = self.make_advice()
        self.client.force_authenticate(self.advisor)
        self.client.delete(advice_detail_url(advice.id))

        response = self.client.post(
            self.advices_url(),
            self.create_payload(directional_guidance="다시 작성한 조언"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class AdminAdviceListTests(AdviceTestBase):
    """SPEC-002 TASK-004 — api.md #32."""

    def test_list_requires_login(self):
        response = self.client.get(ADMIN_ADVICES_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_requires_admin(self):
        self.client.force_authenticate(self.advisor)
        response = self.client.get(ADMIN_ADVICES_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_default_excludes_drafts(self):
        # Owner decision 2026-09-11 (spec.md §7-1): an advisor's unsubmitted
        # draft must never reach the review queue, regardless of status.
        submitted = self.make_advice(is_submitted=True)
        self.make_advice(
            concern=Concern.objects.create(
                author=self.requester,
                concern_summary="초안만 있는 고민",
                concern_type=ConcernType.JOB_CHANGE,
            ),
            is_submitted=False,
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get(ADMIN_ADVICES_URL)

        ids = [item["advice_id"] for item in response.data["items"]]
        self.assertEqual(ids, [str(submitted.id)])

    def test_list_status_filter_still_excludes_drafts(self):
        approved = self.make_advice(status=AdviceStatus.APPROVED, is_submitted=True)
        draft_other_concern = Concern.objects.create(
            author=self.requester,
            concern_summary="다른 고민",
            concern_type=ConcernType.JOB_CHANGE,
        )
        # A draft cannot naturally reach APPROVED through the API, but an
        # admin could hand-edit one in Django Admin — the filter must still
        # exclude it here.
        self.make_advice(
            concern=draft_other_concern,
            advisor=self.other_advisor,
            status=AdviceStatus.APPROVED,
            is_submitted=False,
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get(ADMIN_ADVICES_URL, {"status": AdviceStatus.APPROVED})

        ids = [item["advice_id"] for item in response.data["items"]]
        self.assertEqual(ids, [str(approved.id)])

    def test_list_query_count_is_bounded(self):
        for index in range(5):
            concern = Concern.objects.create(
                author=self.requester,
                concern_summary=f"대량 고민 {index}",
                concern_type=ConcernType.BURNOUT,
            )
            self.make_advice(concern=concern, advisor=self.other_advisor)

        self.client.force_authenticate(self.admin)
        # IsAdmin adds one query (UserRole lookup) beyond the COUNT + page
        # pair — unlike IsActiveAdvisor, which only reads an in-memory
        # attribute. Fixed at 3 regardless of row count (TEST_CRITERIA §3).
        with self.assertNumQueries(3):
            response = self.client.get(ADMIN_ADVICES_URL)
        self.assertEqual(response.data["page_info"]["total"], 5)


class AdviceReviewTests(AdviceTestBase):
    """SPEC-002 TASK-004 — api.md #33, the atomic side-effect core."""

    def review_payload(self, **overrides):
        payload = {"decision": "approved", "expected_version": 1}
        payload.update(overrides)
        return payload

    def test_review_requires_admin(self):
        advice = self.make_advice()
        self.client.force_authenticate(self.advisor)
        response = self.client.patch(
            advice_review_url(advice.id), self.review_payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_approve_transitions_advice_and_concern_and_notifies(self):
        advice = self.make_advice()

        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            advice_review_url(advice.id), self.review_payload(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], AdviceStatus.APPROVED)
        self.assertEqual(response.data["concern_status"], ConcernStatus.ANSWERED)
        self.assertEqual(response.data["review"]["decision"], "approved")
        self.assertEqual(response.data["review"]["reviewed_by"], str(self.admin.id))

        advice.refresh_from_db()
        self.assertEqual(advice.status, AdviceStatus.APPROVED)
        self.concern.refresh_from_db()
        self.assertEqual(self.concern.status, ConcernStatus.ANSWERED)

        notification = Notification.objects.get(recipient=self.requester)
        self.assertEqual(notification.type, NotificationType.ADVICE_APPROVED)

    def test_approve_does_not_revert_closed_concern(self):
        # Owner decision 2026-09-11 (spec.md §7-3): §6.6 has no
        # CLOSED->ANSWERED edge, so approval must not touch a CLOSED concern.
        self.concern.status = ConcernStatus.CLOSED
        self.concern.save(update_fields=["status"])
        advice = self.make_advice()

        self.client.force_authenticate(self.admin)
        self.client.patch(
            advice_review_url(advice.id), self.review_payload(), format="json"
        )

        self.concern.refresh_from_db()
        self.assertEqual(self.concern.status, ConcernStatus.CLOSED)

    def test_approve_leaves_already_answered_concern_unchanged(self):
        self.concern.status = ConcernStatus.ANSWERED
        self.concern.save(update_fields=["status"])
        advice = self.make_advice()

        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            advice_review_url(advice.id), self.review_payload(), format="json"
        )

        self.assertEqual(response.data["concern_status"], ConcernStatus.ANSWERED)

    def test_reject_notifies_advisor_and_leaves_concern_unchanged(self):
        advice = self.make_advice()

        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            advice_review_url(advice.id),
            self.review_payload(decision="rejected", reason="근거 보강이 필요합니다."),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], AdviceStatus.REJECTED)

        advice.refresh_from_db()
        self.assertEqual(advice.reject_reason, "근거 보강이 필요합니다.")
        self.concern.refresh_from_db()
        self.assertEqual(self.concern.status, ConcernStatus.ASSIGNED)

        notification = Notification.objects.get(recipient=self.advisor)
        self.assertEqual(notification.type, NotificationType.ADVICE_REJECTED)

    def test_reject_without_reason_returns_422(self):
        advice = self.make_advice()

        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            advice_review_url(advice.id),
            self.review_payload(decision="rejected"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_version_mismatch_returns_412(self):
        advice = self.make_advice()

        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            advice_review_url(advice.id),
            self.review_payload(expected_version=99),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_412_PRECONDITION_FAILED)

    def test_reviewing_already_approved_advice_returns_409(self):
        advice = self.make_advice(status=AdviceStatus.APPROVED)

        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            advice_review_url(advice.id), self.review_payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_reviewing_draft_returns_409(self):
        # Owner decision 2026-09-11 (spec.md §7-1): a draft is not eligible
        # for review even if someone calls this endpoint directly.
        advice = self.make_advice(is_submitted=False)

        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            advice_review_url(advice.id), self.review_payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_reviewing_state_is_allowed(self):
        advice = self.make_advice(status=AdviceStatus.REVIEWING)

        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            advice_review_url(advice.id), self.review_payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_nonexistent_advice_returns_404(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            advice_review_url("00000000-0000-7000-8000-000000000000"),
            self.review_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_failed_review_leaves_no_partial_state(self):
        # 409 path (already APPROVED): no second notification, no re-review.
        advice = self.make_advice(status=AdviceStatus.APPROVED)

        self.client.force_authenticate(self.admin)
        self.client.patch(
            advice_review_url(advice.id),
            self.review_payload(expected_version=1),
            format="json",
        )

        self.assertFalse(Notification.objects.exists())
        self.concern.refresh_from_db()
        self.assertEqual(self.concern.status, ConcernStatus.ASSIGNED)


class ReceivedAdviceListTests(AdviceTestBase):
    """SPEC-002 TASK-005 — api.md #26. §6.2's user-facing exposure rule."""

    def other_persons_concern(self):
        stranger = User.objects.create_user(
            email="stranger@example.com", nickname="stranger", password="pw12345!"
        )
        return Concern.objects.create(
            author=stranger,
            concern_summary="남의 고민",
            concern_type=ConcernType.BURNOUT,
        )

    def test_list_requires_login(self):
        response = self.client.get(RECEIVED_ADVICES_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_shows_only_approved_advices_on_own_concerns(self):
        approved = self.make_advice(status=AdviceStatus.APPROVED)
        # Same concern, a different advisor, still PENDING -> must not leak.
        self.make_advice(advisor=self.other_advisor, status=AdviceStatus.PENDING)
        # An APPROVED advice on someone else's concern -> must not leak.
        self.make_advice(
            concern=self.other_persons_concern(),
            advisor=self.other_advisor,
            status=AdviceStatus.APPROVED,
        )

        self.client.force_authenticate(self.requester)
        response = self.client.get(RECEIVED_ADVICES_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("page_info", response.data)
        ids = [item["advice_id"] for item in response.data["items"]]
        self.assertEqual(ids, [str(approved.id)])

    def test_list_hides_rejected_and_deleted(self):
        for advice_status in (AdviceStatus.REJECTED, AdviceStatus.DELETED):
            concern = Concern.objects.create(
                author=self.requester,
                concern_summary=f"{advice_status} 고민",
                concern_type=ConcernType.BURNOUT,
            )
            self.make_advice(concern=concern, status=advice_status)

        self.client.force_authenticate(self.requester)
        response = self.client.get(RECEIVED_ADVICES_URL)
        self.assertEqual(response.data["items"], [])

    def test_list_is_feedback_submitted_reflects_feedback_rows(self):
        without_feedback = self.make_advice(status=AdviceStatus.APPROVED)
        second_concern = Concern.objects.create(
            author=self.requester,
            concern_summary="피드백 남긴 고민",
            concern_type=ConcernType.BURNOUT,
        )
        with_feedback = self.make_advice(
            concern=second_concern, status=AdviceStatus.APPROVED
        )
        Feedback.objects.create(advice=with_feedback, author=self.requester, score=5)

        self.client.force_authenticate(self.requester)
        response = self.client.get(RECEIVED_ADVICES_URL)

        by_id = {item["advice_id"]: item for item in response.data["items"]}
        self.assertTrue(by_id[str(with_feedback.id)]["is_feedback_submitted"])
        self.assertFalse(by_id[str(without_feedback.id)]["is_feedback_submitted"])

    def test_list_uses_advisor_application_display_name(self):
        AdvisorApplication.objects.create(
            applicant=self.advisor,
            display_name="활동명조언가",
            domain_category=DomainCategory.HR_ORG,
            experience_band=ExperienceBand.BAND_5_7,
            current_status=CurrentStatus.EMPLOYED,
            intended_lane=IntendedLane.EXPERT,
            career_narrative="경력",
            advisable_concern_types=[ConcernType.BURNOUT],
            sample_advice_response="샘플",
            status=AdvisorApplicationStatus.APPROVED,
        )
        self.make_advice(status=AdviceStatus.APPROVED)

        self.client.force_authenticate(self.requester)
        response = self.client.get(RECEIVED_ADVICES_URL)

        item = response.data["items"][0]
        self.assertEqual(item["advisor_display_name"], "활동명조언가")
        self.assertNotIn("advisor_user_id", item)

    def test_list_keyword_filters_on_concern_summary(self):
        self.make_advice(status=AdviceStatus.APPROVED)
        target_concern = Concern.objects.create(
            author=self.requester,
            concern_summary="이직 고민입니다",
            concern_type=ConcernType.JOB_CHANGE,
        )
        target = self.make_advice(concern=target_concern, status=AdviceStatus.APPROVED)

        self.client.force_authenticate(self.requester)
        response = self.client.get(RECEIVED_ADVICES_URL, {"keyword": "이직"})

        ids = [item["advice_id"] for item in response.data["items"]]
        self.assertEqual(ids, [str(target.id)])

    def test_list_date_range_filter(self):
        advice = self.make_advice(status=AdviceStatus.APPROVED)
        created = advice.created_at.date().isoformat()

        self.client.force_authenticate(self.requester)
        included = self.client.get(
            RECEIVED_ADVICES_URL, {"from_date": created, "to_date": created}
        )
        self.assertEqual(len(included.data["items"]), 1)

        excluded = self.client.get(RECEIVED_ADVICES_URL, {"from_date": "2099-01-01"})
        self.assertEqual(len(excluded.data["items"]), 0)

    def test_list_query_count_is_bounded(self):
        for index in range(5):
            concern = Concern.objects.create(
                author=self.requester,
                concern_summary=f"대량 고민 {index}",
                concern_type=ConcernType.BURNOUT,
            )
            self.make_advice(concern=concern, status=AdviceStatus.APPROVED)

        self.client.force_authenticate(self.requester)
        # Measured, not guessed (see README_AIUSAGE 2026-09-11 TASK-004):
        # COUNT + the page + one bulk display-name lookup = 3, flat in the
        # number of rows. An N+1 display-name lookup would make this 7.
        with self.assertNumQueries(3):
            response = self.client.get(RECEIVED_ADVICES_URL)
        self.assertEqual(response.data["page_info"]["total"], 5)


class FeedbackCreateTests(AdviceTestBase):
    """SPEC-002 TASK-005 — api.md #34."""

    def setUp(self):
        super().setUp()
        self.approved_advice = self.make_advice(status=AdviceStatus.APPROVED)

    def test_create_requires_login(self):
        response = self.client.post(
            feedbacks_url(self.approved_advice.id), {"score": 5}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_success(self):
        self.client.force_authenticate(self.requester)
        response = self.client.post(
            feedbacks_url(self.approved_advice.id),
            {"score": 4, "content": "방향을 잡는 데 도움이 됐습니다."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], FeedbackStatus.SUBMITTED)
        self.assertEqual(response.data["advice_id"], str(self.approved_advice.id))

        feedback = Feedback.objects.get(pk=response.data["feedback_id"])
        self.assertEqual(feedback.author, self.requester)
        self.assertEqual(feedback.score, 4)

    def test_create_on_pending_advice_forbidden(self):
        # §6.2: a non-APPROVED advice is not visible to the user at all, so
        # it cannot be the target of feedback either.
        pending = self.make_advice(advisor=self.other_advisor)

        self.client.force_authenticate(self.requester)
        response = self.client.post(
            feedbacks_url(pending.id), {"score": 5}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_by_non_owner_forbidden(self):
        bystander = User.objects.create_user(
            email="bystander2@example.com", nickname="bystander2", password="pw12345!"
        )

        self.client.force_authenticate(bystander)
        response = self.client.post(
            feedbacks_url(self.approved_advice.id), {"score": 5}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_duplicate_returns_409(self):
        Feedback.objects.create(
            advice=self.approved_advice, author=self.requester, score=3
        )

        self.client.force_authenticate(self.requester)
        response = self.client.post(
            feedbacks_url(self.approved_advice.id), {"score": 5}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_create_rejects_out_of_range_score(self):
        self.client.force_authenticate(self.requester)
        for invalid_score in (0, 6):
            response = self.client.post(
                feedbacks_url(self.approved_advice.id),
                {"score": invalid_score},
                format="json",
            )
            self.assertEqual(
                response.status_code,
                status.HTTP_400_BAD_REQUEST,
                msg=f"score={invalid_score} should be rejected",
            )

    def test_create_on_missing_advice_returns_404(self):
        self.client.force_authenticate(self.requester)
        response = self.client.post(
            feedbacks_url("00000000-0000-7000-8000-000000000000"),
            {"score": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class MyFeedbackListTests(AdviceTestBase):
    """SPEC-002 TASK-005 — api.md #35."""

    def test_list_requires_login(self):
        response = self.client.get(MY_FEEDBACKS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_only_own_feedbacks(self):
        mine_advice = self.make_advice(status=AdviceStatus.APPROVED)
        mine = Feedback.objects.create(
            advice=mine_advice, author=self.requester, score=5, content="좋았어요"
        )

        stranger = User.objects.create_user(
            email="stranger2@example.com", nickname="stranger2", password="pw12345!"
        )
        stranger_concern = Concern.objects.create(
            author=stranger,
            concern_summary="남의 고민",
            concern_type=ConcernType.BURNOUT,
        )
        stranger_advice = self.make_advice(
            concern=stranger_concern,
            advisor=self.other_advisor,
            status=AdviceStatus.APPROVED,
        )
        Feedback.objects.create(advice=stranger_advice, author=stranger, score=2)

        self.client.force_authenticate(self.requester)
        response = self.client.get(MY_FEEDBACKS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("page_info", response.data)
        ids = [item["feedback_id"] for item in response.data["items"]]
        self.assertEqual(ids, [str(mine.id)])
        self.assertEqual(response.data["items"][0]["content"], "좋았어요")

    def test_list_query_count_is_bounded(self):
        for index in range(5):
            concern = Concern.objects.create(
                author=self.requester,
                concern_summary=f"피드백 고민 {index}",
                concern_type=ConcernType.BURNOUT,
            )
            advice = self.make_advice(concern=concern, status=AdviceStatus.APPROVED)
            Feedback.objects.create(
                advice=advice, author=self.requester, score=index % 5 + 1
            )

        self.client.force_authenticate(self.requester)
        # Measured: COUNT + the page. No derived fields here, so nothing else.
        with self.assertNumQueries(2):
            response = self.client.get(MY_FEEDBACKS_URL)
        self.assertEqual(response.data["page_info"]["total"], 5)


class AdminFeedbackTestBase(AdviceTestBase):
    """Shared fixture for #36~#38: an APPROVED advice with a feedback on it."""

    def setUp(self):
        super().setUp()
        self.approved_advice = self.make_advice(status=AdviceStatus.APPROVED)
        self.feedback = Feedback.objects.create(
            advice=self.approved_advice,
            author=self.requester,
            score=4,
            content="도움이 됐습니다.",
        )

    def make_feedback(self, score=3, feedback_status=FeedbackStatus.SUBMITTED):
        """A second feedback on a fresh concern/advice pair."""
        concern = Concern.objects.create(
            author=self.requester,
            concern_summary=f"추가 고민 {score}",
            concern_type=ConcernType.BURNOUT,
        )
        advice = self.make_advice(
            concern=concern, advisor=self.other_advisor, status=AdviceStatus.APPROVED
        )
        return Feedback.objects.create(
            advice=advice, author=self.requester, score=score, status=feedback_status
        )


class AdminFeedbackListTests(AdminFeedbackTestBase):
    """SPEC-002 TASK-006 — api.md #36."""

    def test_list_requires_login(self):
        response = self.client.get(ADMIN_FEEDBACKS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_requires_admin(self):
        self.client.force_authenticate(self.requester)
        response = self.client.get(ADMIN_FEEDBACKS_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_exposes_both_parties(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(ADMIN_FEEDBACKS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data["items"][0]
        self.assertEqual(item["feedback_id"], str(self.feedback.id))
        self.assertEqual(item["advice_id"], str(self.approved_advice.id))
        self.assertEqual(item["author_user_id"], str(self.requester.id))
        self.assertEqual(item["advisor_user_id"], str(self.advisor.id))
        # The list stays light: no body text (CLAUDE.md §8).
        self.assertNotIn("content", item)

    def test_list_status_filter(self):
        reviewed = self.make_feedback(score=5, feedback_status=FeedbackStatus.REVIEWED)

        self.client.force_authenticate(self.admin)
        response = self.client.get(
            ADMIN_FEEDBACKS_URL, {"status": FeedbackStatus.REVIEWED}
        )

        ids = [item["feedback_id"] for item in response.data["items"]]
        self.assertEqual(ids, [str(reviewed.id)])

    def test_list_score_range_filter(self):
        low = self.make_feedback(score=1)
        self.make_feedback(score=5)

        self.client.force_authenticate(self.admin)
        response = self.client.get(
            ADMIN_FEEDBACKS_URL, {"score_min": 1, "score_max": 2}
        )

        ids = [item["feedback_id"] for item in response.data["items"]]
        self.assertEqual(ids, [str(low.id)])

    def test_list_rejects_invalid_score_filter(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(ADMIN_FEEDBACKS_URL, {"score_min": 9})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_query_count_is_bounded(self):
        for score in range(1, 6):
            self.make_feedback(score=score)

        self.client.force_authenticate(self.admin)
        # Measured, not guessed: IsAdmin's UserRole check + COUNT + the page.
        # advisor_user_id/author come from select_related joins, so the count
        # stays flat as rows grow (TEST_CRITERIA §3).
        with self.assertNumQueries(3):
            response = self.client.get(ADMIN_FEEDBACKS_URL)
        self.assertEqual(response.data["page_info"]["total"], 6)


class AdminFeedbackDetailTests(AdminFeedbackTestBase):
    """SPEC-002 TASK-006 — api.md #37."""

    def test_detail_requires_admin(self):
        self.client.force_authenticate(self.requester)
        response = self.client.get(admin_feedback_url(self.feedback.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_nonexistent_returns_404(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(
            admin_feedback_url("00000000-0000-7000-8000-000000000000")
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_exposes_admin_only_fields(self):
        self.feedback.memo = "운영 메모"
        self.feedback.save(update_fields=["memo"])

        self.client.force_authenticate(self.admin)
        response = self.client.get(admin_feedback_url(self.feedback.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["author_nickname"], self.requester.nickname)
        self.assertEqual(response.data["content"], "도움이 됐습니다.")
        self.assertEqual(response.data["memo"], "운영 메모")
        self.assertIn("reviewed_at", response.data)
        self.assertIn("reviewed_by", response.data)


class AdminFeedbackTransitionTests(AdminFeedbackTestBase):
    """SPEC-002 TASK-006 — api.md #38. §6.3's one-way status flow."""

    def patch_status(self, feedback, new_status, **extra):
        payload = {"status": new_status}
        payload.update(extra)
        return self.client.patch(
            admin_feedback_url(feedback.id), payload, format="json"
        )

    def test_transition_requires_admin(self):
        self.client.force_authenticate(self.requester)
        response = self.patch_status(self.feedback, FeedbackStatus.REVIEWED)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_submitted_to_reviewed_records_reviewer(self):
        self.client.force_authenticate(self.admin)
        response = self.patch_status(self.feedback, FeedbackStatus.REVIEWED)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], FeedbackStatus.REVIEWED)
        self.assertEqual(response.data["reviewed_by"], str(self.admin.id))

        self.feedback.refresh_from_db()
        self.assertEqual(self.feedback.status, FeedbackStatus.REVIEWED)
        self.assertIsNotNone(self.feedback.reviewed_at)
        self.assertEqual(self.feedback.reviewed_by, self.admin)

    def test_reviewed_to_archived(self):
        reviewed = self.make_feedback(feedback_status=FeedbackStatus.REVIEWED)

        self.client.force_authenticate(self.admin)
        response = self.patch_status(reviewed, FeedbackStatus.ARCHIVED)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reviewed.refresh_from_db()
        self.assertEqual(reviewed.status, FeedbackStatus.ARCHIVED)

    def test_skipping_reviewed_returns_409(self):
        self.client.force_authenticate(self.admin)
        response = self.patch_status(self.feedback, FeedbackStatus.ARCHIVED)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_reverse_transition_returns_409(self):
        archived = self.make_feedback(feedback_status=FeedbackStatus.ARCHIVED)

        self.client.force_authenticate(self.admin)
        response = self.patch_status(archived, FeedbackStatus.REVIEWED)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_same_status_returns_409(self):
        self.client.force_authenticate(self.admin)
        response = self.patch_status(self.feedback, FeedbackStatus.SUBMITTED)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_memo_is_stored_alongside_transition(self):
        self.client.force_authenticate(self.admin)
        response = self.patch_status(
            self.feedback, FeedbackStatus.REVIEWED, memo="확인 완료"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.feedback.refresh_from_db()
        self.assertEqual(self.feedback.memo, "확인 완료")

    def test_invalid_status_returns_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            admin_feedback_url(self.feedback.id),
            {"status": "NOT_A_STATUS"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_returns_404(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            admin_feedback_url("00000000-0000-7000-8000-000000000000"),
            {"status": FeedbackStatus.REVIEWED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
