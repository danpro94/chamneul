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

from accounts.models import ActiveRole, Role, UserRole
from advice import services as advice_services
from advisors import services as advisor_services
from advisors.models import (
    AdvisorApplication,
    AdvisorApplicationStatus,
    CurrentStatus,
    DomainCategory,
    ExperienceBand,
    IntendedLane,
)
from common.taxonomy import ConcernType
from concerns import services as concern_services
from concerns.models import AssignmentPriority, Concern, TriageDecision

from .models import Notification, NotificationType

User = get_user_model()

NOTIFICATIONS_URL = "/api/v1/notifications"


def notification_url(notification_id):
    return f"/api/v1/notifications/{notification_id}"


def read_url(notification_id):
    return f"/api/v1/notifications/{notification_id}/read"


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


class NotificationReadTests(NotificationTestBase):
    """PATCH /api/v1/notifications/{notification-id}/read (#41).

    api.md #41's status set has no 409, so re-reading an already-read
    notification is idempotent (200), not a conflict. The invariant that makes
    it idempotent rather than merely tolerant: `read_at` keeps its *first*
    value — "처음 읽은 시각"이 나중 호출로 덮어써지면 감사 정보가 사라진다.
    """

    def test_marking_unread_notification_sets_flag_and_timestamp(self):
        notification = self.make_notification(self.me, is_read=False)

        self.client.force_authenticate(self.me)
        response = self.client.patch(read_url(notification.id))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_read"])
        self.assertIsNotNone(response.data["read_at"])

        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_response_fields(self):
        # api.md #41 Response: notification_id / is_read / read_at 만.
        notification = self.make_notification(self.me, is_read=False)

        self.client.force_authenticate(self.me)
        response = self.client.patch(read_url(notification.id))

        self.assertEqual(set(response.data), {"notification_id", "is_read", "read_at"})
        self.assertEqual(response.data["notification_id"], str(notification.id))

    def test_rereading_is_idempotent_and_preserves_first_read_at(self):
        notification = self.make_notification(self.me, is_read=True)
        first_read_at = notification.read_at

        self.client.force_authenticate(self.me)
        response = self.client.patch(read_url(notification.id))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_read"])
        notification.refresh_from_db()
        self.assertEqual(notification.read_at, first_read_at)

    def test_unread_count_drops_after_read(self):
        first = self.make_notification(self.me, is_read=False)
        self.make_notification(self.me, is_read=False)

        self.client.force_authenticate(self.me)
        self.assertEqual(self.client.get(NOTIFICATIONS_URL).data["unread_count"], 2)

        self.client.patch(read_url(first.id))

        self.assertEqual(self.client.get(NOTIFICATIONS_URL).data["unread_count"], 1)

    def test_reading_one_does_not_touch_the_others(self):
        target = self.make_notification(self.me, is_read=False)
        untouched = self.make_notification(self.me, is_read=False)

        self.client.force_authenticate(self.me)
        self.client.patch(read_url(target.id))

        untouched.refresh_from_db()
        self.assertFalse(untouched.is_read)
        self.assertIsNone(untouched.read_at)

    def test_cannot_read_another_users_notification(self):
        """404, and the row must stay unread — a failed call may not have
        touched the other user's data."""
        notification = self.make_notification(self.other, is_read=False)

        self.client.force_authenticate(self.me)
        response = self.client.patch(read_url(notification.id))

        self.assertEqual(response.status_code, 404)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

    def test_unknown_id_is_404(self):
        self.client.force_authenticate(self.me)
        response = self.client.patch(
            read_url("00000000-0000-0000-0000-000000000000")
        )
        self.assertEqual(response.status_code, 404)

    def test_requires_authentication(self):
        notification = self.make_notification(self.me, is_read=False)
        response = self.client.patch(read_url(notification.id))
        self.assertEqual(response.status_code, 401)


class NotificationTargetUrlRoundTripTests(TestCase):
    """AC-8 — C-10 `target_url` 규약이 실제로 동작하는가 (api.md #39).

    이 프로젝트에서 알림은 SPEC-001·002·M4-4가 **쓰기만** 해 온 데이터다.
    다섯 개 서비스가 `target_url`에 상대 경로를 문자열로 박아 넣었지만,
    읽는 코드가 없었으므로 **그 경로를 실제로 호출해 본 적이 한 번도 없다.**
    여기서 5종을 전부 실제 서비스 경로로 발생시키고, 각 `target_url`을
    수신자 본인 세션으로 GET해 200이 나오는지 확인한다.

    이것이 잡아내는 결함: 오타, 라우트 개편으로 깨진 경로, 수신자가 접근할
    수 없는 경로(예: 신청 결과 알림이 admin 전용 #14를 가리키는 경우).
    """

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="rt.admin@example.com", nickname="rtadmin", password="pw12345!"
        )
        UserRole.objects.create(user=self.admin, role=Role.ADMIN)
        self.owner = User.objects.create_user(
            email="rt.owner@example.com", nickname="rtowner", password="pw12345!"
        )
        self.advisor = User.objects.create_user(
            email="rt.advisor@example.com", nickname="rtadvisor", password="pw12345!"
        )
        UserRole.objects.create(user=self.advisor, role=Role.ADVISOR)
        self.advisor.active_role = ActiveRole.ADVISOR
        self.advisor.save(update_fields=["active_role"])

    def make_concern(self):
        return Concern.objects.create(
            author=self.owner,
            concern_summary="이직을 할지 남을지 결정해야 합니다",
            concern_type=ConcernType.JOB_CHANGE,
            decision_context="3년차, 제안 2건",
        )

    def make_application(self, status):
        return AdvisorApplication.objects.create(
            applicant=self.owner,
            display_name=f"신청자-{status}",
            domain_category=DomainCategory.HR_ORG,
            experience_band=ExperienceBand.BAND_5_7,
            current_status=CurrentStatus.EMPLOYED,
            intended_lane=IntendedLane.EXPERT,
            career_narrative="경력 서술",
            advisable_concern_types=[ConcernType.BURNOUT],
            sample_advice_response="샘플 답변",
            status=status,
        )

    def assert_reachable(self, notification, viewer, payload_keys):
        """수신자 본인 세션으로 target_url을 GET해 200인지 확인한다.

        `payload_keys`는 api.md C-10 표가 타입별로 요구하는 부가 식별자다.
        클라이언트 리졸버가 `(type, target_url)`로 목적지를 정하고 나머지
        식별자는 payload에서 꺼내므로, 키가 빠지면 화면 이동이 불완전해진다.
        """
        self.assertTrue(
            notification.target_url.startswith("/api/v1/"),
            f"{notification.type}: target_url은 /api/v1/로 시작해야 한다",
        )
        self.assertNotIn("?", notification.target_url)
        self.assertFalse(notification.target_url.endswith("/"))

        missing = payload_keys - set(notification.payload)
        self.assertFalse(
            missing, f"{notification.type}: payload에 {missing}가 없다 (C-10)"
        )

        self.client.force_authenticate(viewer)
        response = self.client.get(notification.target_url)
        self.assertEqual(
            response.status_code,
            200,
            f"{notification.type}: 수신자가 {notification.target_url}를 열 수 없다",
        )

    def test_assignment_created_target_url_is_reachable_by_the_advisor(self):
        concern = self.make_concern()
        concern_services.assign_advisor(
            concern.id,
            actor=self.admin,
            validated_data={
                "advisor_user_id": str(self.advisor.id),
                "triage_decision": TriageDecision.SUITABLE,
                "priority": AssignmentPriority.NORMAL,
            },
        )

        notification = Notification.objects.get(
            type=NotificationType.ASSIGNMENT_CREATED
        )
        self.assertEqual(notification.recipient_id, self.advisor.id)
        self.assertEqual(notification.payload.get("concern_id"), str(concern.id))
        # 결정 2026-09-16 — 알림 본문은 고민 요약의 사본을 담지 않는다. 사본은
        # 원본의 접근 규칙을 상속하지 않아 배정 해제·역할 회수·소프트 삭제
        # 이후에도 계속 읽히기 때문이다 (리뷰 S-2/AR-08).
        self.assertNotIn(concern.concern_summary, notification.message)
        self.assertNotIn(concern.concern_summary, notification.title)
        self.assert_reachable(
            notification, self.advisor, {"concern_id", "assignment_id"}
        )

    def test_advice_approved_target_url_is_reachable_by_the_concern_owner(self):
        concern = self.make_concern()
        concern_services.assign_advisor(
            concern.id,
            actor=self.admin,
            validated_data={
                "advisor_user_id": str(self.advisor.id),
                "triage_decision": TriageDecision.SUITABLE,
                "priority": AssignmentPriority.NORMAL,
            },
        )
        advice = advice_services.create_advice(
            concern.id,
            self.advisor,
            {
                "directional_guidance": "두 선택지의 5년 후를 적어보세요.",
                "reflective_questions": ["무엇이 두려운가요?"],
                "considerations": "연봉 외 요소",
                "submit": True,
            },
        )
        advice_services.review_advice(
            advice.id,
            actor=self.admin,
            decision=advice_services.DECISION_APPROVED,
            reason="",
            expected_version=advice.version,
        )

        notification = Notification.objects.get(type=NotificationType.ADVICE_APPROVED)
        self.assertEqual(notification.recipient_id, self.owner.id)
        self.assert_reachable(
            notification, self.owner, {"advice_id", "concern_id"}
        )

    def test_advice_rejected_target_url_is_reachable_by_the_advisor(self):
        concern = self.make_concern()
        concern_services.assign_advisor(
            concern.id,
            actor=self.admin,
            validated_data={
                "advisor_user_id": str(self.advisor.id),
                "triage_decision": TriageDecision.SUITABLE,
                "priority": AssignmentPriority.NORMAL,
            },
        )
        advice = advice_services.create_advice(
            concern.id,
            self.advisor,
            {
                "directional_guidance": "두 선택지의 5년 후를 적어보세요.",
                "reflective_questions": ["무엇이 두려운가요?"],
                "considerations": "연봉 외 요소",
                "submit": True,
            },
        )
        advice_services.review_advice(
            advice.id,
            actor=self.admin,
            decision=advice_services.DECISION_REJECTED,
            reason="근거가 부족합니다",
            expected_version=advice.version,
        )

        notification = Notification.objects.get(type=NotificationType.ADVICE_REJECTED)
        self.assertEqual(notification.recipient_id, self.advisor.id)
        self.assert_reachable(
            notification, self.advisor, {"advice_id", "concern_id"}
        )

    def test_application_approved_target_url_is_reachable_by_the_applicant(self):
        application = self.make_application(AdvisorApplicationStatus.REVIEWING)
        advisor_services.review_application(
            application.id,
            actor=self.admin,
            target_status=AdvisorApplicationStatus.APPROVED,
        )

        notification = Notification.objects.get(
            type=NotificationType.ADVISOR_APPLICATION_APPROVED
        )
        self.assertEqual(notification.recipient_id, self.owner.id)
        # 신청자가 열 수 있는 #12를 가리켜야 한다 (admin 전용 #14가 아니라).
        self.assertEqual(notification.target_url, "/api/v1/advisor-applications/me")
        self.assert_reachable(notification, self.owner, {"application_id"})

    def test_application_rejected_target_url_is_reachable_by_the_applicant(self):
        application = self.make_application(AdvisorApplicationStatus.REVIEWING)
        advisor_services.review_application(
            application.id,
            actor=self.admin,
            target_status=AdvisorApplicationStatus.REJECTED,
            reject_reason="경력 서술이 부족합니다",
        )

        notification = Notification.objects.get(
            type=NotificationType.ADVISOR_APPLICATION_REJECTED
        )
        self.assertEqual(notification.recipient_id, self.owner.id)
        self.assert_reachable(notification, self.owner, {"application_id"})

    def test_every_notification_type_is_covered_by_this_class(self):
        """5종 중 하나라도 빠지면 이 테스트가 알려준다 — 타입이 추가되면
        왕복 검증도 함께 추가하라는 신호다 (CLAUDE.md §6.4는 5종 고정)."""
        covered = {
            NotificationType.ASSIGNMENT_CREATED,
            NotificationType.ADVICE_APPROVED,
            NotificationType.ADVICE_REJECTED,
            NotificationType.ADVISOR_APPLICATION_APPROVED,
            NotificationType.ADVISOR_APPLICATION_REJECTED,
        }
        self.assertEqual(covered, set(NotificationType.values))


class NotificationQueryValidationTests(NotificationTestBase):
    """#39 쿼리 파라미터 검증 (Owner 결정 2026-09-16, 리뷰 AR-02).

    이전 구현은 알 수 없는 값을 조용히 무시했다. 그 결과 `?is_read=banana`는
    "안 읽은 것만 보여줘"라는 요청에 **읽은 것까지 전부** 돌려줬고, 필터가
    버려졌다는 신호도 없었다. SPEC-002가 이틀 전 #26·#31·#32에 세운 선례와도
    반대 방향이었다.
    """

    def test_unparseable_is_read_is_400(self):
        self.make_notification(self.me, is_read=True)

        self.client.force_authenticate(self.me)
        response = self.client.get(NOTIFICATIONS_URL, {"is_read": "banana"})

        self.assertEqual(response.status_code, 400)

    def test_unknown_type_is_400(self):
        self.client.force_authenticate(self.me)
        response = self.client.get(NOTIFICATIONS_URL, {"type": "NOPE"})

        self.assertEqual(response.status_code, 400)

    def test_absent_filters_still_return_everything(self):
        self.make_notification(self.me, is_read=True)
        self.make_notification(self.me, is_read=False)

        self.client.force_authenticate(self.me)
        response = self.client.get(NOTIFICATIONS_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["items"]), 2)

    def test_state_changing_request_requires_csrf(self):
        """`force_authenticate`는 인증기를 통째로 건너뛰므로 다른 테스트에서는
        `CsrfSessionAuthentication.enforce_csrf`가 한 번도 실행되지 않는다.
        실제 세션 로그인으로 그 경로를 한 번은 지나가게 한다 (리뷰 S-8)."""
        notification = self.make_notification(self.me, is_read=False)
        client = APIClient(enforce_csrf_checks=True)
        client.login(email="me@example.com", password="pw12345!")

        response = client.patch(read_url(notification.id))

        self.assertEqual(response.status_code, 403)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)
