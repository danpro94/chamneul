"""Tests for concerns API (SPEC-001 TASK-001, api.md #16-#17).

Written before views/serializers/services exist (specs/SPEC-001-concerns-api/
tasks.md — TDD: this file must fail first, then pass after implementation).
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

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
