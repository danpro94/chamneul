"""Tests for concerns API (SPEC-001, api.md #16-#19).

Written before the code they exercise exists (specs/SPEC-001-concerns-api/
tasks.md — TDD: each test class must fail first, then pass after
implementation).
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

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

from .models import Concern, ConcernStatus

User = get_user_model()

CONCERNS_URL = "/api/v1/users/me/concerns"


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
