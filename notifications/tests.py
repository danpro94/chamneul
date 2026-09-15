"""Tests for the notifications API (SPEC-003, api.md #39-#41).

Written before the code they exercise exists (specs/SPEC-003-notifications-
roles/tasks.md — TDD: each test must fail first).

Access control here is queryset scope, not an ownership comparison: every
lookup is filtered to `recipient=request.user`, so another user's notification
is 404 and its existence is never revealed (spec.md §7 결정 2 — Owner: "알림은
나에게만"). The tests assert 404 rather than 403 to pin that down.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Notification, NotificationType

User = get_user_model()

NOTIFICATIONS_URL = "/api/v1/notifications"


def notification_url(notification_id):
    return f"/api/v1/notifications/{notification_id}"


class NotificationTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.me = User.objects.create_user(
            email="me@example.com", nickname="me", password="pw12345!"
        )
        self.other = User.objects.create_user(
            email="other@example.com", nickname="other", password="pw12345!"
        )
        self.actor = User.objects.create_user(
            email="actor@example.com", nickname="actor", password="pw12345!"
        )

    def make_notification(self, recipient=None, *, type=None, is_read=False, title="알림"):
        """One notification. `actor_user` is always set so the tests can prove
        the admin's identity is *not* serialized (spec.md §7 결정 1)."""
        return Notification.objects.create(
            recipient=recipient or self.me,
            type=type or NotificationType.ADVICE_APPROVED,
            title=title,
            message="본문",
            target_url="/api/v1/advices/00000000-0000-0000-0000-000000000000",
            actor_user=self.actor,
            payload={"advice_id": "x"},
            is_read=is_read,
            read_at=timezone.now() if is_read else None,
        )


class NotificationListTests(NotificationTestBase):
    """GET /api/v1/notifications (#39)."""

    def test_returns_only_my_notifications(self):
        self.make_notification(self.me, title="내 것 1")
        self.make_notification(self.me, title="내 것 2")
        self.make_notification(self.other, title="남의 것")

        self.client.force_authenticate(self.me)
        response = self.client.get(NOTIFICATIONS_URL)

        self.assertEqual(response.status_code, 200)
        titles = [item["title"] for item in response.data["items"]]
        self.assertEqual(len(titles), 2)
        self.assertNotIn("남의 것", titles)

    def test_unread_count_matches_unread_notifications(self):
        self.make_notification(self.me, is_read=True)
        self.make_notification(self.me, is_read=False)
        self.make_notification(self.me, is_read=False)
        self.make_notification(self.other, is_read=False)  # 남의 미읽음은 세지 않는다

        self.client.force_authenticate(self.me)
        response = self.client.get(NOTIFICATIONS_URL)

        self.assertEqual(response.data["unread_count"], 2)

    def test_is_read_filter_narrows_items_but_not_unread_count(self):
        # 뱃지 숫자가 필터에 따라 흔들리면 안 된다 (spec.md §4).
        self.make_notification(self.me, is_read=True)
        self.make_notification(self.me, is_read=False)
        self.make_notification(self.me, is_read=False)

        self.client.force_authenticate(self.me)
        response = self.client.get(NOTIFICATIONS_URL, {"is_read": "false"})

        self.assertEqual(len(response.data["items"]), 2)
        self.assertTrue(all(item["is_read"] is False for item in response.data["items"]))
        self.assertEqual(response.data["unread_count"], 2)

    def test_is_read_true_filter_returns_read_only(self):
        self.make_notification(self.me, is_read=True)
        self.make_notification(self.me, is_read=False)

        self.client.force_authenticate(self.me)
        response = self.client.get(NOTIFICATIONS_URL, {"is_read": "true"})

        self.assertEqual(len(response.data["items"]), 1)
        self.assertTrue(response.data["items"][0]["is_read"])

    def test_type_filter(self):
        self.make_notification(self.me, type=NotificationType.ADVICE_APPROVED)
        self.make_notification(self.me, type=NotificationType.ADVICE_REJECTED)
        self.make_notification(self.me, type=NotificationType.ASSIGNMENT_CREATED)

        self.client.force_authenticate(self.me)
        response = self.client.get(
            NOTIFICATIONS_URL, {"type": NotificationType.ADVICE_REJECTED}
        )

        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(
            response.data["items"][0]["type"], NotificationType.ADVICE_REJECTED
        )

    def test_combined_filters(self):
        self.make_notification(
            self.me, type=NotificationType.ADVICE_APPROVED, is_read=True
        )
        self.make_notification(
            self.me, type=NotificationType.ADVICE_APPROVED, is_read=False
        )
        self.make_notification(
            self.me, type=NotificationType.ADVICE_REJECTED, is_read=False
        )

        self.client.force_authenticate(self.me)
        response = self.client.get(
            NOTIFICATIONS_URL,
            {"type": NotificationType.ADVICE_APPROVED, "is_read": "false"},
        )

        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(
            response.data["items"][0]["type"], NotificationType.ADVICE_APPROVED
        )
        self.assertFalse(response.data["items"][0]["is_read"])

    def test_newest_first(self):
        first = self.make_notification(self.me, title="먼저")
        second = self.make_notification(self.me, title="나중")

        self.client.force_authenticate(self.me)
        response = self.client.get(NOTIFICATIONS_URL)

        ids = [item["notification_id"] for item in response.data["items"]]
        self.assertEqual(ids, [str(second.id), str(first.id)])

    def test_page_info_present(self):
        self.make_notification(self.me)

        self.client.force_authenticate(self.me)
        response = self.client.get(NOTIFICATIONS_URL)

        self.assertEqual(
            set(response.data["page_info"]), {"page", "size", "total", "total_pages"}
        )
        self.assertEqual(response.data["page_info"]["total"], 1)

    def test_empty_inbox(self):
        self.client.force_authenticate(self.me)
        response = self.client.get(NOTIFICATIONS_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["items"], [])
        self.assertEqual(response.data["unread_count"], 0)

    def test_list_item_fields(self):
        # api.md #39: 목록은 read_at을 싣지 않는다 (상세 전용).
        self.make_notification(self.me)

        self.client.force_authenticate(self.me)
        response = self.client.get(NOTIFICATIONS_URL)

        self.assertEqual(
            set(response.data["items"][0]),
            {
                "notification_id",
                "type",
                "title",
                "message",
                "target_url",
                "is_read",
                "created_at",
            },
        )

    def test_requires_authentication(self):
        response = self.client.get(NOTIFICATIONS_URL)
        self.assertEqual(response.status_code, 401)

    def test_query_count_is_constant(self):
        for _ in range(5):
            self.make_notification(self.me)

        self.client.force_authenticate(self.me)
        # 실측 3건: 페이지네이션 COUNT + 페이지 행 + unread_count 집계.
        # select_related가 없는 이유는 응답 필드가 전부 자기 컬럼이기 때문이다.
        with self.assertNumQueries(3):
            self.client.get(NOTIFICATIONS_URL)


class NotificationDetailTests(NotificationTestBase):
    """GET /api/v1/notifications/{notification-id} (#40)."""

    def test_recipient_can_read_own_notification(self):
        notification = self.make_notification(self.me)

        self.client.force_authenticate(self.me)
        response = self.client.get(notification_url(notification.id))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["notification_id"], str(notification.id))

    def test_read_at_is_null_when_unread(self):
        notification = self.make_notification(self.me, is_read=False)

        self.client.force_authenticate(self.me)
        response = self.client.get(notification_url(notification.id))

        self.assertIn("read_at", response.data)
        self.assertIsNone(response.data["read_at"])

    def test_read_at_present_when_read(self):
        notification = self.make_notification(self.me, is_read=True)

        self.client.force_authenticate(self.me)
        response = self.client.get(notification_url(notification.id))

        self.assertIsNotNone(response.data["read_at"])

    def test_detail_fields(self):
        notification = self.make_notification(self.me)

        self.client.force_authenticate(self.me)
        response = self.client.get(notification_url(notification.id))

        self.assertEqual(
            set(response.data),
            {
                "notification_id",
                "type",
                "title",
                "message",
                "target_url",
                "is_read",
                "read_at",
                "created_at",
            },
        )

    def test_actor_identity_is_never_exposed(self):
        """spec.md §7 결정 1 — 5개 알림 타입의 actor는 전부 관리자다. 응답에
        관리자 계정 id가 실리면 일반 사용자에게 admin 신원이 새어 나간다."""
        notification = self.make_notification(self.me)

        self.client.force_authenticate(self.me)
        response = self.client.get(notification_url(notification.id))

        self.assertNotIn("actor", response.data)
        self.assertNotIn("actor_user", response.data)
        body = str(response.data)
        self.assertNotIn(str(self.actor.id), body)
        self.assertNotIn(self.actor.email, body)

    def test_other_users_notification_is_404_not_403(self):
        """결정 2 — 존재 자체를 숨긴다. 403이면 'id는 있다'는 정보가 샌다."""
        notification = self.make_notification(self.other)

        self.client.force_authenticate(self.me)
        response = self.client.get(notification_url(notification.id))

        self.assertEqual(response.status_code, 404)

    def test_unknown_id_is_404(self):
        self.client.force_authenticate(self.me)
        response = self.client.get(
            notification_url("00000000-0000-0000-0000-000000000000")
        )
        self.assertEqual(response.status_code, 404)

    def test_requires_authentication(self):
        notification = self.make_notification(self.me)
        response = self.client.get(notification_url(notification.id))
        self.assertEqual(response.status_code, 401)
