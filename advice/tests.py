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
from common.taxonomy import ConcernType
from concerns.models import Assignment, Concern, ConcernStatus, TriageDecision

from .models import Advice, AdviceStatus

User = get_user_model()

ADVICES_WRITTEN_URL = "/api/v1/users/me/advices-written"


def advice_detail_url(advice_id):
    return f"/api/v1/advices/{advice_id}"


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
