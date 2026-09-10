"""Tests for concerns API (SPEC-001, api.md #16-#23).

Written before the code they exercise exists (specs/SPEC-001-concerns-api/
tasks.md — TDD: each test class must fail first, then pass after
implementation).
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import ActiveRole, Role, UserRole
from advice.models import Advice, AdviceStatus
from advisors.models import (
    AdvisorApplication,
    AdvisorApplicationStatus,
    CurrentStatus,
    DomainCategory,
    ExperienceBand,
    IntendedLane,
)
from common.taxonomy import ConcernType

from .models import Assignment, Concern, ConcernStatus, TriageDecision

User = get_user_model()

CONCERNS_URL = "/api/v1/users/me/concerns"
ASSIGNED_CONCERNS_URL = "/api/v1/users/me/assigned-concerns"
ADMIN_CONCERNS_URL = "/api/v1/admin/concerns"


class ConcernCreateListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.author = User.objects.create_user(
            email="author@example.com", nickname="author", password="pw12345!"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com", nickname="other", password="pw12345!"
        )

    # --- AC-1 : create (#16) -------------------------------------------

    def test_create_requires_login(self):
        response = self.client.post(
            CONCERNS_URL,
            {"concern_summary": "고민", "concern_type": ConcernType.BURNOUT},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_success(self):
        self.client.force_authenticate(self.author)
        response = self.client.post(
            CONCERNS_URL,
            {"concern_summary": "이직할지 고민이에요", "concern_type": ConcernType.JOB_CHANGE},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], ConcernStatus.SUBMITTED)
        self.assertIn("concern_id", response.data)
        self.assertIn("message", response.data)

        concern = Concern.objects.get(pk=response.data["concern_id"])
        self.assertEqual(concern.author, self.author)
        self.assertIsNone(concern.deleted_at)

    def test_create_rejects_unknown_concern_type(self):
        self.client.force_authenticate(self.author)
        response = self.client.post(
            CONCERNS_URL,
            {"concern_summary": "고민", "concern_type": "not_a_real_type"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_rejects_too_many_secondary_types(self):
        self.client.force_authenticate(self.author)
        response = self.client.post(
            CONCERNS_URL,
            {
                "concern_summary": "고민",
                "concern_type": ConcernType.BURNOUT,
                # size=2 on the model (concerns/models.py) — 3 must be rejected.
                "concern_type_secondary": [
                    ConcernType.JOB_CHANGE,
                    ConcernType.RELATIONSHIP,
                    ConcernType.RELOCATION,
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_rejects_summary_over_100_chars(self):
        self.client.force_authenticate(self.author)
        response = self.client.post(
            CONCERNS_URL,
            {"concern_summary": "가" * 101, "concern_type": ConcernType.BURNOUT},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- AC-2 : list (#17) ------------------------------------------------

    def test_list_requires_login(self):
        response = self.client.get(CONCERNS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_only_own_non_deleted_concerns(self):
        mine = Concern.objects.create(
            author=self.author, concern_summary="내 고민", concern_type=ConcernType.BURNOUT
        )
        Concern.objects.create(
            author=self.other_user,
            concern_summary="남의 고민",
            concern_type=ConcernType.BURNOUT,
        )
        deleted = Concern.objects.create(
            author=self.author,
            concern_summary="지운 고민",
            concern_type=ConcernType.BURNOUT,
        )
        deleted.deleted_at = deleted.created_at  # soft-deleted (CLAUDE.md §6.6)
        deleted.save(update_fields=["deleted_at"])

        self.client.force_authenticate(self.author)
        response = self.client.get(CONCERNS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("page_info", response.data)
        ids = [item["concern_id"] for item in response.data["items"]]
        self.assertEqual(ids, [str(mine.id)])

    def test_list_status_filter(self):
        Concern.objects.create(
            author=self.author,
            concern_summary="제출됨",
            concern_type=ConcernType.BURNOUT,
            status=ConcernStatus.SUBMITTED,
        )
        answered = Concern.objects.create(
            author=self.author,
            concern_summary="답변됨",
            concern_type=ConcernType.BURNOUT,
            status=ConcernStatus.ANSWERED,
        )

        self.client.force_authenticate(self.author)
        response = self.client.get(CONCERNS_URL, {"status": ConcernStatus.ANSWERED})

        ids = [item["concern_id"] for item in response.data["items"]]
        self.assertEqual(ids, [str(answered.id)])


class ConcernDetailDeleteTests(TestCase):
    """SPEC-001 TASK-002 (api.md #18 detail, #19 soft delete)."""

    def setUp(self):
        self.client = APIClient()
        self.author = User.objects.create_user(
            email="author2@example.com", nickname="author2", password="pw12345!"
        )
        self.other_user = User.objects.create_user(
            email="other2@example.com", nickname="other2", password="pw12345!"
        )
        self.advisor = User.objects.create_user(
            email="advisor@example.com", nickname="advisor", password="pw12345!"
        )
        self.concern = Concern.objects.create(
            author=self.author,
            concern_summary="상세 조회 테스트",
            concern_type=ConcernType.BURNOUT,
        )

    def detail_url(self, concern_id):
        return f"{CONCERNS_URL}/{concern_id}"

    def _approve_advisor(self, advisor, display_name):
        AdvisorApplication.objects.create(
            applicant=advisor,
            display_name=display_name,
            domain_category=DomainCategory.HR_ORG,
            experience_band=ExperienceBand.BAND_5_7,
            current_status=CurrentStatus.EMPLOYED,
            intended_lane=IntendedLane.EXPERT,
            career_narrative="경력 서술",
            advisable_concern_types=[ConcernType.BURNOUT],
            sample_advice_response="샘플 답변",
            status=AdvisorApplicationStatus.APPROVED,
        )

    # --- AC-3 : detail (#18) ------------------------------------------

    def test_detail_requires_login(self):
        response = self.client.get(self.detail_url(self.concern.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_detail_owner_sees_only_approved_advice(self):
        self._approve_advisor(self.advisor, "번아웃전문가")
        approved = Advice.objects.create(
            concern=self.concern,
            advisor=self.advisor,
            directional_guidance="승인된 조언",
            status=AdviceStatus.APPROVED,
        )
        Advice.objects.create(
            concern=self.concern,
            advisor=self.other_user,
            directional_guidance="대기중 조언",
            status=AdviceStatus.PENDING,
        )

        self.client.force_authenticate(self.author)
        response = self.client.get(self.detail_url(self.concern.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        advice_ids = [a["advice_id"] for a in response.data["approved_advices"]]
        self.assertEqual(advice_ids, [str(approved.id)])
        self.assertEqual(
            response.data["approved_advices"][0]["advisor_display_name"], "번아웃전문가"
        )

    def test_detail_soft_deleted_returns_404(self):
        self.concern.deleted_at = timezone.now()
        self.concern.save(update_fields=["deleted_at"])

        self.client.force_authenticate(self.author)
        response = self.client.get(self.detail_url(self.concern.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_others_concern_returns_404(self):
        self.client.force_authenticate(self.other_user)
        response = self.client.get(self.detail_url(self.concern.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- AC-4 : soft delete (#19) --------------------------------------

    def test_delete_requires_login(self):
        response = self.client.delete(self.detail_url(self.concern.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_success_marks_deleted_at_and_preserves_children(self):
        Advice.objects.create(
            concern=self.concern,
            advisor=self.advisor,
            directional_guidance="보존되어야 하는 조언",
            status=AdviceStatus.APPROVED,
        )

        self.client.force_authenticate(self.author)
        response = self.client.delete(self.detail_url(self.concern.id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.concern.refresh_from_db()
        self.assertIsNotNone(self.concern.deleted_at)
        self.assertEqual(Advice.objects.filter(concern=self.concern).count(), 1)

        # Now invisible through the owner's own GET — soft delete, not admin.
        get_response = self.client.get(self.detail_url(self.concern.id))
        self.assertEqual(get_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_already_deleted_returns_409(self):
        self.concern.deleted_at = timezone.now()
        self.concern.save(update_fields=["deleted_at"])

        self.client.force_authenticate(self.author)
        response = self.client.delete(self.detail_url(self.concern.id))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_delete_others_concern_returns_404(self):
        self.client.force_authenticate(self.other_user)
        response = self.client.delete(self.detail_url(self.concern.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AssignedConcernTests(TestCase):
    """SPEC-001 TASK-003 (api.md #20 assigned list, #21 assigned detail)."""

    def setUp(self):
        self.client = APIClient()
        self.requester = User.objects.create_user(
            email="requester@example.com", nickname="requester", password="pw12345!"
        )
        self.assigner = User.objects.create_user(
            email="assigner@example.com", nickname="assigner", password="pw12345!"
        )
        self.advisor = User.objects.create_user(
            email="advisor3@example.com", nickname="advisor3", password="pw12345!"
        )
        UserRole.objects.create(user=self.advisor, role=Role.ADVISOR)
        self.advisor.active_role = ActiveRole.ADVISOR
        self.advisor.save(update_fields=["active_role"])

        # Holds ADVISOR but hasn't switched into it (still browsing as USER).
        self.advisor_wrong_mode = User.objects.create_user(
            email="advisor4@example.com", nickname="advisor4", password="pw12345!"
        )
        UserRole.objects.create(user=self.advisor_wrong_mode, role=Role.ADVISOR)

        self.no_role_user = User.objects.create_user(
            email="norole@example.com", nickname="norole", password="pw12345!"
        )

        self.assigned_concern = Concern.objects.create(
            author=self.requester,
            concern_summary="배정된 고민",
            concern_type=ConcernType.BURNOUT,
        )
        self.assignment = Assignment.objects.create(
            concern=self.assigned_concern,
            advisor=self.advisor,
            assigned_by=self.assigner,
            triage_decision=TriageDecision.SUITABLE,
        )
        # Not assigned to self.advisor — used to prove list/detail scoping.
        self.unassigned_concern = Concern.objects.create(
            author=self.requester,
            concern_summary="배정 안 된 고민",
            concern_type=ConcernType.BURNOUT,
        )

    def detail_url(self, concern_id):
        return f"{ASSIGNED_CONCERNS_URL}/{concern_id}"

    # --- AC-5 : assigned list (#20) -------------------------------------

    def test_list_requires_login(self):
        response = self.client.get(ASSIGNED_CONCERNS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_requires_advisor_role(self):
        self.client.force_authenticate(self.no_role_user)
        response = self.client.get(ASSIGNED_CONCERNS_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_requires_active_role_advisor(self):
        # Holds ADVISOR but active_role is still USER (default) -> 403.
        self.client.force_authenticate(self.advisor_wrong_mode)
        response = self.client.get(ASSIGNED_CONCERNS_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_returns_only_own_assignments(self):
        self.client.force_authenticate(self.advisor)
        response = self.client.get(ASSIGNED_CONCERNS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["concern_id"] for item in response.data["items"]]
        self.assertEqual(ids, [str(self.assigned_concern.id)])
        self.assertIsNone(response.data["items"][0]["advice_status"])

    def test_list_reflects_own_advice_status(self):
        Advice.objects.create(
            concern=self.assigned_concern,
            advisor=self.advisor,
            directional_guidance="작성 중인 조언",
            status=AdviceStatus.REVIEWING,
        )

        self.client.force_authenticate(self.advisor)
        response = self.client.get(ASSIGNED_CONCERNS_URL)

        self.assertEqual(response.data["items"][0]["advice_status"], AdviceStatus.REVIEWING)

    # --- AC-6 : assigned detail (#21) -----------------------------------

    def test_detail_requires_login(self):
        response = self.client.get(self.detail_url(self.assigned_concern.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_detail_not_assigned_returns_403(self):
        self.client.force_authenticate(self.advisor)
        response = self.client.get(self.detail_url(self.unassigned_concern.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_nonexistent_concern_returns_404(self):
        self.client.force_authenticate(self.advisor)
        response = self.client.get(self.detail_url("00000000-0000-7000-8000-000000000000"))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_requester_display_name_prefers_alias(self):
        self.assigned_concern.display_alias = "이직고민러"
        self.assigned_concern.is_anonymous = False
        self.assigned_concern.save(update_fields=["display_alias", "is_anonymous"])

        self.client.force_authenticate(self.advisor)
        response = self.client.get(self.detail_url(self.assigned_concern.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["requester_display_name"], "이직고민러")

    def test_detail_requester_display_name_anonymous_fallback(self):
        self.assigned_concern.display_alias = ""
        self.assigned_concern.is_anonymous = True
        self.assigned_concern.save(update_fields=["display_alias", "is_anonymous"])

        self.client.force_authenticate(self.advisor)
        response = self.client.get(self.detail_url(self.assigned_concern.id))

        self.assertEqual(response.data["requester_display_name"], "익명의 요청자")

    def test_detail_requester_display_name_nickname_fallback(self):
        self.assigned_concern.display_alias = ""
        self.assigned_concern.is_anonymous = False
        self.assigned_concern.save(update_fields=["display_alias", "is_anonymous"])

        self.client.force_authenticate(self.advisor)
        response = self.client.get(self.detail_url(self.assigned_concern.id))

        self.assertEqual(response.data["requester_display_name"], self.requester.nickname)

    def test_detail_never_exposes_email_or_user_id(self):
        self.client.force_authenticate(self.advisor)
        response = self.client.get(self.detail_url(self.assigned_concern.id))

        self.assertNotIn("email", response.data)
        self.assertNotIn("user_id", response.data)
        self.assertNotIn("author_id", response.data)

    def test_detail_includes_my_advice_when_present(self):
        advice = Advice.objects.create(
            concern=self.assigned_concern,
            advisor=self.advisor,
            directional_guidance="내 조언",
            status=AdviceStatus.PENDING,
        )

        self.client.force_authenticate(self.advisor)
        response = self.client.get(self.detail_url(self.assigned_concern.id))

        self.assertEqual(response.data["my_advice"]["advice_id"], str(advice.id))
        self.assertEqual(response.data["my_advice"]["status"], AdviceStatus.PENDING)
        self.assertEqual(response.data["my_advice"]["version"], 1)
        self.assertTrue(response.data["my_advice"]["is_submitted"])

    def test_detail_my_advice_is_none_when_absent(self):
        self.client.force_authenticate(self.advisor)
        response = self.client.get(self.detail_url(self.assigned_concern.id))

        self.assertIsNone(response.data["my_advice"])


class AdminConcernTests(TestCase):
    """SPEC-001 TASK-004 (api.md #22 admin list, #23 admin detail)."""

    def setUp(self):
        self.client = APIClient()
        self.author = User.objects.create_user(
            email="author5@example.com", nickname="author5", password="pw12345!"
        )
        self.advisor = User.objects.create_user(
            email="advisor5@example.com", nickname="advisor5", password="pw12345!"
        )
        UserRole.objects.create(user=self.advisor, role=Role.ADVISOR)
        self.admin = User.objects.create_user(
            email="admin5@example.com", nickname="admin5", password="pw12345!"
        )
        UserRole.objects.create(user=self.admin, role=Role.ADMIN)

        self.alive_concern = Concern.objects.create(
            author=self.author,
            concern_summary="살아있는 고민",
            concern_type=ConcernType.BURNOUT,
            status=ConcernStatus.ASSIGNED,
        )
        self.deleted_concern = Concern.objects.create(
            author=self.author,
            concern_summary="삭제된 고민",
            concern_type=ConcernType.JOB_CHANGE,
        )
        self.deleted_concern.deleted_at = timezone.now()
        self.deleted_concern.save(update_fields=["deleted_at"])

    def detail_url(self, concern_id):
        return f"{ADMIN_CONCERNS_URL}/{concern_id}"

    # --- AC-7 : admin list (#22) ----------------------------------------

    def test_list_requires_login(self):
        response = self.client.get(ADMIN_CONCERNS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_requires_admin(self):
        self.client.force_authenticate(self.author)
        response = self.client.get(ADMIN_CONCERNS_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_excludes_deleted_by_default(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(ADMIN_CONCERNS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["concern_id"] for item in response.data["items"]]
        self.assertEqual(ids, [str(self.alive_concern.id)])

    def test_list_include_deleted_shows_both_with_is_deleted_flag(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(ADMIN_CONCERNS_URL, {"include_deleted": "true"})

        by_id = {item["concern_id"]: item for item in response.data["items"]}
        self.assertEqual(len(by_id), 2)
        self.assertFalse(by_id[str(self.alive_concern.id)]["is_deleted"])
        self.assertTrue(by_id[str(self.deleted_concern.id)]["is_deleted"])

    def test_list_status_filter(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(ADMIN_CONCERNS_URL, {"status": ConcernStatus.ASSIGNED})

        ids = [item["concern_id"] for item in response.data["items"]]
        self.assertEqual(ids, [str(self.alive_concern.id)])

    def test_list_keyword_filter(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(ADMIN_CONCERNS_URL, {"keyword": "살아있는"})

        ids = [item["concern_id"] for item in response.data["items"]]
        self.assertEqual(ids, [str(self.alive_concern.id)])

    def test_list_reports_active_assignment_count(self):
        active = Assignment.objects.create(
            concern=self.alive_concern,
            advisor=self.advisor,
            assigned_by=self.admin,
            triage_decision=TriageDecision.SUITABLE,
        )
        # A deactivated assignment must not inflate the count.
        Assignment.objects.create(
            concern=self.alive_concern,
            advisor=self.author,
            assigned_by=self.admin,
            triage_decision=TriageDecision.SUITABLE,
            is_active=False,
        )
        self.assertTrue(active.is_active)

        self.client.force_authenticate(self.admin)
        response = self.client.get(ADMIN_CONCERNS_URL)

        item = response.data["items"][0]
        self.assertEqual(item["assignment_count"], 1)
        self.assertEqual(item["author_user_id"], str(self.author.id))

    # --- AC-8 : admin detail (#23) --------------------------------------

    def test_detail_requires_admin(self):
        self.client.force_authenticate(self.author)
        response = self.client.get(self.detail_url(self.alive_concern.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_nonexistent_returns_404(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.detail_url("00000000-0000-7000-8000-000000000000"))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_includes_deleted_concern(self):
        # Admin/audit access reaches soft-deleted rows (CLAUDE.md §6.6) —
        # otherwise include_deleted=true in #22 would list unreachable rows.
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.detail_url(self.deleted_concern.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_deleted"])

    def test_detail_shows_all_assignments_and_advices_regardless_of_state(self):
        AdvisorApplication.objects.create(
            applicant=self.advisor,
            display_name="배정된조언가",
            domain_category=DomainCategory.HR_ORG,
            experience_band=ExperienceBand.BAND_5_7,
            current_status=CurrentStatus.EMPLOYED,
            intended_lane=IntendedLane.EXPERT,
            career_narrative="경력 서술",
            advisable_concern_types=[ConcernType.BURNOUT],
            sample_advice_response="샘플 답변",
            status=AdvisorApplicationStatus.APPROVED,
        )
        active_assignment = Assignment.objects.create(
            concern=self.alive_concern,
            advisor=self.advisor,
            assigned_by=self.admin,
            triage_decision=TriageDecision.SUITABLE,
        )
        inactive_assignment = Assignment.objects.create(
            concern=self.alive_concern,
            advisor=self.author,
            assigned_by=self.admin,
            triage_decision=TriageDecision.OUT_OF_SCOPE,
            is_active=False,
        )
        pending_advice = Advice.objects.create(
            concern=self.alive_concern,
            advisor=self.advisor,
            directional_guidance="대기중 조언",
            status=AdviceStatus.PENDING,
        )
        approved_advice = Advice.objects.create(
            concern=self.alive_concern,
            advisor=self.author,
            directional_guidance="승인된 조언",
            status=AdviceStatus.APPROVED,
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get(self.detail_url(self.alive_concern.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assignment_ids = {a["assignment_id"] for a in response.data["assignments"]}
        self.assertEqual(
            assignment_ids, {str(active_assignment.id), str(inactive_assignment.id)}
        )
        # §6.2's APPROVED-only rule protects concern owners, not admins.
        advice_ids = {a["advice_id"] for a in response.data["advices"]}
        self.assertEqual(advice_ids, {str(pending_advice.id), str(approved_advice.id)})

        advisor_row = next(
            a
            for a in response.data["assignments"]
            if a["assignment_id"] == str(active_assignment.id)
        )
        self.assertEqual(advisor_row["advisor_display_name"], "배정된조언가")
        self.assertTrue(advisor_row["is_active"])

    def test_detail_query_count_is_bounded(self):
        for index in range(5):
            advisor = User.objects.create_user(
                email=f"bulk{index}@example.com",
                nickname=f"bulk{index}",
                password="pw12345!",
            )
            Assignment.objects.create(
                concern=self.alive_concern,
                advisor=advisor,
                assigned_by=self.admin,
                triage_decision=TriageDecision.SUITABLE,
            )
            Advice.objects.create(
                concern=self.alive_concern,
                advisor=advisor,
                directional_guidance=f"조언 {index}",
                status=AdviceStatus.PENDING,
            )

        self.client.force_authenticate(self.admin)
        # Fixed budget: IsAdmin check + concern + assignments + advices + one
        # bulk display-name lookup = 5. With 5 assignments and 5 advices, an
        # N+1 implementation would land near 15 — this pins the constant.
        with self.assertNumQueries(5):
            response = self.client.get(self.detail_url(self.alive_concern.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["assignments"]), 5)
