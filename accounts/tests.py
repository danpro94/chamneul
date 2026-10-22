"""Tests for the admin role grant/revoke API (SPEC-003, api.md #42-#43).

The first test file in this app. Its scope is deliberately #42/#43 only —
retrofitting tests for M4-1~M4-3 (signup/login/OAuth/profile), which were
written before the project adopted test-first, is tracked as documentation
debt and is not part of SPEC-003.

Two invariants get more attention than their size suggests, because breaking
either one is an operational incident rather than a bug:
  * granting/revoking a role must never send a notification (ADR-003 §4);
  * the system must never end up with zero administrators (ADR-003 §2).
"""

import json
import re
import smtplib
import sys
import urllib.error
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sessions.models import Session
from django.core import mail
from django.core.signals import got_request_exception
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.debug import ExceptionReporter
from rest_framework.test import APIClient

from advice import services as advice_services
from common.taxonomy import ConcernType
from concerns import services as concern_services
from concerns.models import (
    Assignment,
    AssignmentPriority,
    Concern,
    ConcernStatus,
    TriageDecision,
)
from notifications.models import Notification, NotificationType

from . import oauth
from .models import (
    ActiveRole,
    GoogleIdentity,
    Role,
    RoleGrant,
    RoleGrantAction,
    UserRole,
)

User = get_user_model()


def roles_url(user_id):
    return f"/api/v1/admin/users/{user_id}/roles"


class AdminRoleTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@example.com", nickname="admin", password="pw12345!"
        )
        UserRole.objects.create(user=self.admin, role=Role.ADMIN)
        self.target = User.objects.create_user(
            email="target@example.com", nickname="target", password="pw12345!"
        )
        self.plain = User.objects.create_user(
            email="plain@example.com", nickname="plain", password="pw12345!"
        )


class RoleGrantTests(AdminRoleTestBase):
    """POST /api/v1/admin/users/{user-id}/roles (#42)."""

    def test_grants_advisor_role(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            roles_url(self.target.id), {"role": Role.ADVISOR}, format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            UserRole.objects.filter(user=self.target, role=Role.ADVISOR).exists()
        )

    def test_grants_admin_role(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            roles_url(self.target.id), {"role": Role.ADMIN}, format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            UserRole.objects.filter(user=self.target, role=Role.ADMIN).exists()
        )

    def test_writes_one_audit_row(self):
        self.client.force_authenticate(self.admin)
        self.client.post(
            roles_url(self.target.id),
            {"role": Role.ADVISOR, "reason": "초청 조언가"},
            format="json",
        )

        grants = RoleGrant.objects.filter(user=self.target)
        self.assertEqual(grants.count(), 1)
        grant = grants.get()
        self.assertEqual(grant.role, Role.ADVISOR)
        self.assertEqual(grant.action, RoleGrantAction.GRANT)
        self.assertEqual(grant.acted_by_id, self.admin.id)
        self.assertEqual(grant.reason, "초청 조언가")

    def test_reason_is_optional(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            roles_url(self.target.id), {"role": Role.ADVISOR}, format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(RoleGrant.objects.get(user=self.target).reason, "")

    def test_response_fields(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            roles_url(self.target.id), {"role": Role.ADVISOR}, format="json"
        )

        self.assertEqual(
            set(response.data),
            {"user_id", "roles", "granted_role", "granted_at", "granted_by"},
        )
        self.assertEqual(response.data["user_id"], str(self.target.id))
        self.assertEqual(response.data["granted_role"], Role.ADVISOR)
        self.assertEqual(response.data["granted_by"], str(self.admin.id))
        self.assertIsNotNone(response.data["granted_at"])

    def test_response_roles_reflect_state_after_grant(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            roles_url(self.target.id), {"role": Role.ADVISOR}, format="json"
        )

        # USER is implicit and always first (accounts.services.held_roles).
        self.assertEqual(response.data["roles"], ["USER", "ADVISOR"])

    def test_grant_sends_no_notification(self):
        """ADR-003 §4 — 역할 부여/회수는 알림을 발송하지 않는다."""
        self.client.force_authenticate(self.admin)
        self.client.post(
            roles_url(self.target.id), {"role": Role.ADVISOR}, format="json"
        )

        self.assertFalse(Notification.objects.exists())

    def test_grant_does_not_change_active_role(self):
        """보유와 착용은 다르다 — 전환은 사용자가 #10으로 직접 한다."""
        self.client.force_authenticate(self.admin)
        self.client.post(
            roles_url(self.target.id), {"role": Role.ADVISOR}, format="json"
        )

        self.target.refresh_from_db()
        self.assertEqual(self.target.active_role, ActiveRole.USER)

    def test_granting_an_already_held_role_is_409(self):
        UserRole.objects.create(user=self.target, role=Role.ADVISOR)

        self.client.force_authenticate(self.admin)
        response = self.client.post(
            roles_url(self.target.id), {"role": Role.ADVISOR}, format="json"
        )

        self.assertEqual(response.status_code, 409)

    def test_duplicate_grant_writes_no_audit_row(self):
        """409로 끝난 요청은 감사 기록을 남기지 않는다 — 부여되지 않은 역할이
        부여된 것처럼 보이면 audit trail 자체가 거짓이 된다."""
        UserRole.objects.create(user=self.target, role=Role.ADVISOR)

        self.client.force_authenticate(self.admin)
        self.client.post(
            roles_url(self.target.id), {"role": Role.ADVISOR}, format="json"
        )

        self.assertFalse(RoleGrant.objects.exists())

    def test_user_role_cannot_be_granted(self):
        """USER는 암묵적 기본 역할이라 row로 저장하지 않는다 (model.md §3.2)."""
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            roles_url(self.target.id), {"role": "USER"}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(UserRole.objects.filter(user=self.target).exists())

    def test_unknown_role_is_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            roles_url(self.target.id), {"role": "SUPERADMIN"}, format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_missing_role_is_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(roles_url(self.target.id), {}, format="json")

        self.assertEqual(response.status_code, 400)

    def test_unknown_user_is_404(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            roles_url("00000000-0000-0000-0000-000000000000"),
            {"role": Role.ADVISOR},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_non_admin_is_403(self):
        self.client.force_authenticate(self.plain)
        response = self.client.post(
            roles_url(self.target.id), {"role": Role.ADVISOR}, format="json"
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(UserRole.objects.filter(user=self.target).exists())

    def test_anonymous_is_401(self):
        response = self.client.post(
            roles_url(self.target.id), {"role": Role.ADVISOR}, format="json"
        )

        self.assertEqual(response.status_code, 401)


class RoleRevokeTests(AdminRoleTestBase):
    """DELETE /api/v1/admin/users/{user-id}/roles/{role} (#43).

    The highest-risk endpoint in SPEC-003. Two failure modes are operational
    incidents rather than bugs, and each gets its own cluster of tests:

      * **A-3** — revoking ADVISOR without demoting `active_role` leaves the
        former advisor passing `IsActiveAdvisor`, so #20/#21/#28-#30 stay open
        to someone who is no longer an advisor.
      * **system lockout** — if the "last ADMIN" check and the delete are not
        serialized, two concurrent revokes can each see two admins and leave
        zero. Nobody can grant a role back afterwards.

    Django's TestCase runs inside one transaction, so real concurrency cannot
    be exercised here. What *can* be pinned is that the service re-reads state
    inside its own transaction instead of trusting what the caller saw — the
    same regression shape as A-1 in advisors.services.
    """

    def setUp(self):
        super().setUp()
        self.advisor = User.objects.create_user(
            email="advisor@example.com", nickname="advisor", password="pw12345!"
        )
        UserRole.objects.create(user=self.advisor, role=Role.ADVISOR)
        self.advisor.active_role = ActiveRole.ADVISOR
        self.advisor.save(update_fields=["active_role"])

    def revoke(self, user_id, role, query=""):
        return self.client.delete(f"{roles_url(user_id)}/{role}{query}")

    # --- 정상 경로 ---------------------------------------------------------

    def test_revokes_advisor_role(self):
        self.client.force_authenticate(self.admin)
        response = self.revoke(self.advisor.id, Role.ADVISOR)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            UserRole.objects.filter(user=self.advisor, role=Role.ADVISOR).exists()
        )

    def test_response_has_no_body(self):
        self.client.force_authenticate(self.admin)
        response = self.revoke(self.advisor.id, Role.ADVISOR)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(response.data)

    def test_writes_one_audit_row(self):
        self.client.force_authenticate(self.admin)
        self.revoke(self.advisor.id, Role.ADVISOR, "?reason=활동+중단+요청")

        grants = RoleGrant.objects.filter(user=self.advisor)
        self.assertEqual(grants.count(), 1)
        grant = grants.get()
        self.assertEqual(grant.role, Role.ADVISOR)
        self.assertEqual(grant.action, RoleGrantAction.REVOKE)
        self.assertEqual(grant.acted_by_id, self.admin.id)
        self.assertEqual(grant.reason, "활동 중단 요청")

    def test_reason_is_optional(self):
        self.client.force_authenticate(self.admin)
        self.revoke(self.advisor.id, Role.ADVISOR)

        self.assertEqual(RoleGrant.objects.get(user=self.advisor).reason, "")

    def test_revoke_sends_no_notification(self):
        """ADR-003 §4 — 회수도 알림을 발송하지 않는다."""
        self.client.force_authenticate(self.admin)
        self.revoke(self.advisor.id, Role.ADVISOR)

        self.assertFalse(Notification.objects.exists())

    def test_revoking_one_role_keeps_the_other(self):
        UserRole.objects.create(user=self.advisor, role=Role.ADMIN)

        self.client.force_authenticate(self.admin)
        self.revoke(self.advisor.id, Role.ADVISOR)

        self.assertTrue(
            UserRole.objects.filter(user=self.advisor, role=Role.ADMIN).exists()
        )

    # --- A-3: active_role 강등 ---------------------------------------------

    def test_demotes_active_role_when_the_target_is_wearing_advisor(self):
        """A-3. 강등하지 않으면 자격을 잃은 조언가가 IsActiveAdvisor를 계속
        통과한다 — 권한이 닫히지 않는다."""
        self.assertEqual(self.advisor.active_role, ActiveRole.ADVISOR)

        self.client.force_authenticate(self.admin)
        self.revoke(self.advisor.id, Role.ADVISOR)

        self.advisor.refresh_from_db()
        self.assertEqual(self.advisor.active_role, ActiveRole.USER)

    def test_does_not_touch_active_role_when_the_target_is_not_wearing_it(self):
        self.advisor.active_role = ActiveRole.USER
        self.advisor.save(update_fields=["active_role"])

        self.client.force_authenticate(self.admin)
        self.revoke(self.advisor.id, Role.ADVISOR)

        self.advisor.refresh_from_db()
        self.assertEqual(self.advisor.active_role, ActiveRole.USER)

    def test_admin_revoke_never_touches_active_role(self):
        """ADMIN은 active_role이 될 수 없다 (ActiveRole choices에 없음)."""
        other_admin = User.objects.create_user(
            email="admin2@example.com", nickname="admin2", password="pw12345!"
        )
        UserRole.objects.create(user=other_admin, role=Role.ADMIN)
        UserRole.objects.create(user=other_admin, role=Role.ADVISOR)
        other_admin.active_role = ActiveRole.ADVISOR
        other_admin.save(update_fields=["active_role"])

        self.client.force_authenticate(self.admin)
        self.revoke(other_admin.id, Role.ADMIN)

        other_admin.refresh_from_db()
        self.assertEqual(other_admin.active_role, ActiveRole.ADVISOR)

    # --- 시스템 잠금 방지 --------------------------------------------------

    def test_cannot_revoke_own_admin_role(self):
        User.objects.create_user(
            email="admin2@example.com", nickname="admin2", password="pw12345!"
        )
        UserRole.objects.create(
            user=User.objects.get(email="admin2@example.com"), role=Role.ADMIN
        )

        self.client.force_authenticate(self.admin)
        response = self.revoke(self.admin.id, Role.ADMIN)

        self.assertEqual(response.status_code, 409)
        self.assertTrue(
            UserRole.objects.filter(user=self.admin, role=Role.ADMIN).exists()
        )

    def test_cannot_revoke_the_last_admin(self):
        other_admin = User.objects.create_user(
            email="admin2@example.com", nickname="admin2", password="pw12345!"
        )
        UserRole.objects.create(user=other_admin, role=Role.ADMIN)
        # self.admin 회수 -> 남는 관리자는 other_admin 하나.
        self.client.force_authenticate(other_admin)
        self.assertEqual(self.revoke(self.admin.id, Role.ADMIN).status_code, 204)

        # 이제 other_admin이 마지막 관리자다. 제3의 관리자를 만들어 시도해도
        # (여기서는 superuser) 마지막 UserRole ADMIN은 회수되지 않는다.
        superuser = User.objects.create_user(
            email="root@example.com", nickname="root", password="pw12345!"
        )
        superuser.is_superuser = True
        superuser.save(update_fields=["is_superuser"])

        self.client.force_authenticate(superuser)
        response = self.revoke(other_admin.id, Role.ADMIN)

        self.assertEqual(response.status_code, 409)
        self.assertTrue(
            UserRole.objects.filter(user=other_admin, role=Role.ADMIN).exists()
        )

    def test_last_admin_guard_counts_user_role_rows_not_superusers(self):
        """보수적 판정을 고정한다. IsAdmin은 superuser도 통과시키지만(ADR-003
        §1), 회수 가드는 UserRole 행만 센다 — 잘못 막으면 한 번 더 호출하면
        되지만, 잘못 허용하면 시스템이 잠긴다. 이 비대칭이 기준을 정한다."""
        superuser = User.objects.create_user(
            email="root@example.com", nickname="root", password="pw12345!"
        )
        superuser.is_superuser = True
        superuser.save(update_fields=["is_superuser"])

        # UserRole ADMIN은 self.admin 하나뿐.
        self.client.force_authenticate(superuser)
        response = self.revoke(self.admin.id, Role.ADMIN)

        self.assertEqual(response.status_code, 409)

    def test_can_revoke_admin_while_another_admin_remains(self):
        other_admin = User.objects.create_user(
            email="admin2@example.com", nickname="admin2", password="pw12345!"
        )
        UserRole.objects.create(user=other_admin, role=Role.ADMIN)

        self.client.force_authenticate(self.admin)
        response = self.revoke(other_admin.id, Role.ADMIN)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(UserRole.objects.filter(role=Role.ADMIN).count(), 1)

    def test_guard_reads_state_inside_its_own_transaction(self):
        """A-1과 같은 형태의 회귀 방지. 호출자가 본 상태가 아니라 트랜잭션
        안에서 다시 읽은 상태로 판정해야 한다 — 서비스가 user_id를 받고
        객체를 받지 않는 이유다."""
        other_admin = User.objects.create_user(
            email="admin2@example.com", nickname="admin2", password="pw12345!"
        )
        UserRole.objects.create(user=other_admin, role=Role.ADMIN)

        # 호출 직전에 다른 관리자가 사라진다 (관리자 2명 -> 1명).
        UserRole.objects.filter(user=self.admin, role=Role.ADMIN).delete()

        self.client.force_authenticate(self.admin)  # superuser 아님, 권한은 유지 X
        # 권한을 잃었으므로 403이 정상. 판정 자체는 아래 서비스 호출로 확인한다.
        from accounts import services
        from common.exceptions import Conflict

        with self.assertRaises(Conflict):
            services.revoke_role(other_admin.id, role=Role.ADMIN, actor=self.plain)
        self.assertTrue(
            UserRole.objects.filter(user=other_admin, role=Role.ADMIN).exists()
        )

    # --- 미보유 / 잘못된 입력 ----------------------------------------------

    def test_revoking_a_role_not_held_is_409(self):
        self.client.force_authenticate(self.admin)
        response = self.revoke(self.target.id, Role.ADVISOR)

        self.assertEqual(response.status_code, 409)

    def test_revoking_admin_not_held_is_409_not_last_admin(self):
        """관리자가 1명뿐일 때 ADMIN을 갖지도 않은 사용자를 회수 시도하면,
        '마지막 관리자'가 아니라 '보유하지 않은 역할'로 판정되어야 한다 —
        검사 순서가 뒤집히면 오류 메시지가 사실과 달라진다."""
        self.client.force_authenticate(self.admin)
        response = self.revoke(self.target.id, Role.ADMIN)

        self.assertEqual(response.status_code, 409)
        self.assertIn("보유", str(response.data))

    def test_failed_revoke_leaves_no_partial_state(self):
        self.client.force_authenticate(self.admin)
        self.revoke(self.target.id, Role.ADVISOR)  # 409

        self.assertFalse(RoleGrant.objects.exists())
        self.target.refresh_from_db()
        self.assertEqual(self.target.active_role, ActiveRole.USER)

    def test_user_role_path_is_404(self):
        """USER는 회수 대상이 아니다 (ADR-003 §2). api.md #43의 상태 집합에
        400이 없으므로 URL 패턴 단계에서 매칭을 막아 404로 떨어뜨린다."""
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.revoke(self.target.id, "USER").status_code, 404)

    def test_unknown_role_path_is_404(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.revoke(self.target.id, "SUPERADMIN").status_code, 404)
        self.assertEqual(self.revoke(self.target.id, "advisor").status_code, 404)

    def test_unknown_user_is_404(self):
        self.client.force_authenticate(self.admin)
        response = self.revoke(
            "00000000-0000-0000-0000-000000000000", Role.ADVISOR
        )
        self.assertEqual(response.status_code, 404)

    def test_non_admin_is_403(self):
        self.client.force_authenticate(self.plain)
        response = self.revoke(self.advisor.id, Role.ADVISOR)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            UserRole.objects.filter(user=self.advisor, role=Role.ADVISOR).exists()
        )

    def test_anonymous_is_401(self):
        response = self.revoke(self.advisor.id, Role.ADVISOR)
        self.assertEqual(response.status_code, 401)


class ActiveRoleSwitchTests(AdminRoleTestBase):
    """PATCH /api/v1/users/me/active-role (#10), from the A-3 angle.

    #10 and #43 move the same two facts in opposite directions: one writes
    `active_role`, the other deletes the `UserRole` that justifies it. If they
    interleave unguarded, a switch that *read* a role the revoke then deleted
    still writes it — leaving a user wearing ADVISOR without holding it, which
    is exactly the state A-3 warns about, reached from the other side.
    """

    def setUp(self):
        super().setUp()
        UserRole.objects.create(user=self.target, role=Role.ADVISOR)

    def test_switches_to_a_held_role(self):
        self.client.force_authenticate(self.target)
        response = self.client.patch(
            "/api/v1/users/me/active-role", {"active_role": "ADVISOR"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.target.refresh_from_db()
        self.assertEqual(self.target.active_role, ActiveRole.ADVISOR)

    def test_cannot_switch_to_a_role_not_held(self):
        self.client.force_authenticate(self.plain)
        response = self.client.patch(
            "/api/v1/users/me/active-role", {"active_role": "ADVISOR"}, format="json"
        )

        self.assertEqual(response.status_code, 403)
        self.plain.refresh_from_db()
        self.assertEqual(self.plain.active_role, ActiveRole.USER)

    def test_switch_reads_roles_under_a_row_lock(self):
        """The guard that makes the interleaving above impossible. A switch must
        re-read the role rows while holding the target's `User` row, so a
        concurrent revoke either lands first (and the switch is refused) or
        waits (and sees the ADVISOR still worn, so it demotes)."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from accounts import services

        with CaptureQueriesContext(connection) as ctx:
            services.set_active_role(self.target, "ADVISOR")

        locking = [q["sql"] for q in ctx.captured_queries if "FOR UPDATE" in q["sql"]]
        self.assertTrue(
            locking, "set_active_role must lock the user row before reading roles"
        )
        self.assertIn("accounts_user", locking[0])

    def test_switch_after_revoke_is_refused(self):
        services_target = self.target
        UserRole.objects.filter(user=services_target, role=Role.ADVISOR).delete()

        self.client.force_authenticate(services_target)
        response = self.client.patch(
            "/api/v1/users/me/active-role", {"active_role": "ADVISOR"}, format="json"
        )

        self.assertEqual(response.status_code, 403)


class StateTransitionLockingTests(AdminRoleTestBase):
    """`.claude/rules/coding.md` 상태 전이 규칙을 리뷰가 아니라 테스트로 강제한다.

    세 함수 모두 대상 행을 잠근 뒤에 판정해야 한다. 규칙을 문서로만 두면
    다음 함수가 추가될 때 조용히 빠진다 — A-1이 그렇게 생겼다.
    """

    def capture(self, fn):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            fn()
        return [q["sql"] for q in ctx.captured_queries]

    def test_grant_locks_the_target_user_row(self):
        sqls = self.capture(
            lambda: __import__("accounts.services", fromlist=["x"]).grant_role(
                self.target.id, role=Role.ADVISOR, actor=self.admin
            )
        )
        self.assertTrue(any('FOR UPDATE OF "accounts_user"' in s for s in sqls))

    def test_admin_revoke_locks_the_admin_role_rows_in_a_fixed_order(self):
        other_admin = User.objects.create_user(
            email="admin2@example.com", nickname="admin2", password="pw12345!"
        )
        UserRole.objects.create(user=other_admin, role=Role.ADMIN)

        sqls = self.capture(
            lambda: __import__("accounts.services", fromlist=["x"]).revoke_role(
                other_admin.id, role=Role.ADMIN, actor=self.admin
            )
        )
        locked_set = [s for s in sqls if "accounts_userrole" in s and "FOR UPDATE" in s]
        self.assertTrue(locked_set, "last-admin check must lock the ADMIN role rows")
        # 순서를 고정하지 않으면 두 회수가 반대 순서로 잠가 교착할 수 있다.
        self.assertIn("ORDER BY", locked_set[0])

    def test_revoke_writes_only_the_demoted_column(self):
        advisor = User.objects.create_user(
            email="adv@example.com", nickname="adv", password="pw12345!"
        )
        UserRole.objects.create(user=advisor, role=Role.ADVISOR)
        advisor.active_role = ActiveRole.ADVISOR
        advisor.save(update_fields=["active_role"])

        sqls = self.capture(
            lambda: __import__("accounts.services", fromlist=["x"]).revoke_role(
                advisor.id, role=Role.ADVISOR, actor=self.admin
            )
        )
        updates = [s for s in sqls if s.startswith("UPDATE \"accounts_user\"")]
        self.assertEqual(len(updates), 1)
        # update_fields는 권한 경계다 — 다른 컬럼이 함께 실리면 안 된다.
        self.assertIn('"active_role"', updates[0])
        self.assertIn('"updated_at"', updates[0])
        self.assertNotIn('"email"', updates[0])
        self.assertNotIn('"password"', updates[0])


class RoleRevokeEndToEndTests(TestCase):
    """AC-7 — 회수가 실제로 권한을 닫는가 (SPEC-003 acceptance.md).

    단위 테스트는 `active_role`이 USER로 바뀌었다는 것까지만 증명한다. 정작
    중요한 질문은 그 다음이다: **그래서 조언가가 실제로 막히는가?** 권한은
    `IsActiveAdvisor` -> 뷰 -> 서비스를 거쳐 판정되므로, 그 사슬 전체를
    통과시켜 봐야 A-3가 닫혔다고 말할 수 있다.

    SPEC-002가 AC 전항 통과 + 168개 테스트 상태에서 서브에이전트 리뷰에
    데이터 유실 1건과 500 크래시 1건을 들킨 이유가 이것이었다 — 결함은 개별
    기능이 아니라 **기능 사이**에 있었다.
    """

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="e2e.admin@example.com", nickname="e2eadmin", password="pw12345!"
        )
        UserRole.objects.create(user=self.admin, role=Role.ADMIN)
        self.owner = User.objects.create_user(
            email="e2e.owner@example.com", nickname="e2eowner", password="pw12345!"
        )
        self.advisor = User.objects.create_user(
            email="e2e.advisor@example.com", nickname="e2eadvisor", password="pw12345!"
        )
        UserRole.objects.create(user=self.advisor, role=Role.ADVISOR)
        self.advisor.active_role = ActiveRole.ADVISOR
        self.advisor.save(update_fields=["active_role"])

        self.concern = Concern.objects.create(
            author=self.owner,
            concern_summary="이직을 할지 남을지 결정해야 합니다",
            concern_type=ConcernType.JOB_CHANGE,
            decision_context="3년차, 제안 2건",
        )
        concern_services.assign_advisor(
            self.concern.id,
            actor=self.admin,
            validated_data={
                "advisor_user_id": str(self.advisor.id),
                "triage_decision": TriageDecision.SUITABLE,
                "priority": AssignmentPriority.NORMAL,
            },
        )
        self.advice = advice_services.create_advice(
            self.concern.id,
            self.advisor,
            {
                "directional_guidance": "두 선택지의 5년 후를 적어보세요.",
                "reflective_questions": "무엇이 두려운가요?",
                "considerations": "연봉 외 요소",
                "submit": False,
            },
        )

    def revoke_advisor(self):
        self.client.force_authenticate(self.admin)
        response = self.client.delete(
            f"{roles_url(self.advisor.id)}/{Role.ADVISOR}"
        )
        self.assertEqual(response.status_code, 204)
        # 실제 요청은 세션에서 사용자를 매번 DB에서 다시 읽는다. 반면
        # force_authenticate는 넘겨준 파이썬 객체를 그대로 request.user로
        # 쓰므로, 갱신하지 않으면 강등 전의 active_role이 남아 뒤따르는
        # 검사가 통과해 버린다 — 제품 동작이 아니라 테스트 도구의 성질이다.
        # (지우지 말 것: 지우면 이 클래스의 403 검사가 전부 무의미해진다.)
        self.advisor.refresh_from_db()

    def test_advisor_can_act_before_the_revoke(self):
        """대조군. 회수 후의 403이 '원래부터 막혀 있었다'가 아님을 보장한다."""
        self.client.force_authenticate(self.advisor)
        self.assertEqual(
            self.client.get("/api/v1/users/me/assigned-concerns").status_code, 200
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/advices/{self.advice.id}",
                {"considerations": "회수 전 수정"},
                format="json",
            ).status_code,
            200,
        )

    def test_assigned_concern_list_closes_after_the_revoke(self):
        self.revoke_advisor()

        self.client.force_authenticate(self.advisor)
        response = self.client.get("/api/v1/users/me/assigned-concerns")

        self.assertEqual(response.status_code, 403)

    def test_advice_edit_closes_after_the_revoke(self):
        self.revoke_advisor()

        self.client.force_authenticate(self.advisor)
        response = self.client.patch(
            f"/api/v1/advices/{self.advice.id}",
            {"considerations": "회수 후 수정 — 막혀야 한다"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.advice.refresh_from_db()
        self.assertEqual(self.advice.considerations, "연봉 외 요소")

    def test_revoke_does_not_delete_the_advice_the_advisor_wrote(self):
        """회수는 권한 회수지 데이터 삭제가 아니다. 이미 쓴 조언은 남고,
        작성자 본인은 여전히 읽을 수 있다."""
        self.revoke_advisor()

        self.client.force_authenticate(self.advisor)
        response = self.client.get(f"/api/v1/advices/{self.advice.id}")

        self.assertEqual(response.status_code, 200)

    def test_concern_stays_assigned_after_the_revoke(self):
        """결정 3(a) — 회수는 배정을 자동 해제하지 않는다. 관리자가 #25로
        명시 해제한다. 여기서 고정해 두지 않으면 '자동 해제가 누락된 버그'로
        오인될 수 있는 **의도된** 동작이다."""
        self.revoke_advisor()

        self.concern.refresh_from_db()
        self.assertEqual(self.concern.status, ConcernStatus.ASSIGNED)
        self.assertTrue(
            Assignment.objects.filter(
                concern=self.concern, advisor=self.advisor, is_active=True
            ).exists()
        )

    def test_revoke_leaves_no_notification(self):
        self.revoke_advisor()

        # 배정 시 발생한 ASSIGNMENT_CREATED 1건 외에 새 알림이 없어야 한다.
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(
            Notification.objects.get().type, NotificationType.ASSIGNMENT_CREATED
        )


class RoleGuardHardeningTests(AdminRoleTestBase):
    """2026-09-16 서브에이전트 리뷰 반영분 (S-5·S-6/AR-12·AR-06)."""

    def test_last_admin_guard_ignores_deactivated_administrators(self):
        """S-5. 비활성 계정은 로그인할 수 없으므로(Django ModelBackend), 살아있는
        관리자로 세면 '남은 관리자가 있다'는 판정이 거짓이 된다 — 아무도 역할을
        되돌릴 수 없는 상태가 만들어진다."""
        sleeping_admin = User.objects.create_user(
            email="sleeping@example.com", nickname="sleeping", password="pw12345!"
        )
        UserRole.objects.create(user=sleeping_admin, role=Role.ADMIN)
        sleeping_admin.is_active = False
        sleeping_admin.save(update_fields=["is_active"])

        superuser = User.objects.create_user(
            email="root@example.com", nickname="root", password="pw12345!"
        )
        superuser.is_superuser = True
        superuser.save(update_fields=["is_superuser"])

        # UserRole ADMIN은 2개지만 살아있는 것은 self.admin 하나뿐이다.
        self.client.force_authenticate(superuser)
        response = self.client.delete(f"{roles_url(self.admin.id)}/{Role.ADMIN}")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["error"]["details"]["reason"], "LAST_ADMIN")

    def test_service_layer_rejects_user_role_directly(self):
        """S-6/AR-12. API는 serializer choices와 URL 컨버터로 두 번 막지만,
        관리 커맨드나 향후 admin action은 그 둘을 거치지 않는다."""
        from rest_framework.exceptions import ValidationError

        from accounts import services

        with self.assertRaises(ValidationError):
            services.grant_role(self.target.id, role=Role.USER, actor=self.admin)
        with self.assertRaises(ValidationError):
            services.revoke_role(self.target.id, role=Role.USER, actor=self.admin)
        self.assertFalse(UserRole.objects.filter(role=Role.USER).exists())
        self.assertFalse(RoleGrant.objects.exists())

    def test_conflict_reasons_are_distinguishable(self):
        """AR-06. #43은 세 가지 다른 상황에 409를 준다. 운영 도구가 '이미 없는
        역할'과 '시스템 잠금 방지'를 한국어 문장으로 구분할 수는 없다."""
        other_admin = User.objects.create_user(
            email="admin2@example.com", nickname="admin2", password="pw12345!"
        )
        UserRole.objects.create(user=other_admin, role=Role.ADMIN)

        self.client.force_authenticate(self.admin)

        self_revoke = self.client.delete(f"{roles_url(self.admin.id)}/{Role.ADMIN}")
        self.assertEqual(self_revoke.status_code, 409)
        self.assertEqual(self_revoke.data["error"]["details"]["reason"], "SELF_REVOKE")

        not_held = self.client.delete(f"{roles_url(self.target.id)}/{Role.ADVISOR}")
        self.assertEqual(not_held.status_code, 409)
        self.assertEqual(not_held.data["error"]["details"]["reason"], "NOT_HELD")

        already_held = self.client.post(
            roles_url(other_admin.id), {"role": Role.ADMIN}, format="json"
        )
        self.assertEqual(already_held.status_code, 409)
        self.assertEqual(
            already_held.data["error"]["details"]["reason"], "ALREADY_HELD"
        )

    def test_admin_role_screen_is_view_only(self):
        """결정 A. Django Admin에서 UserRole을 손으로 고치면 강등도 감사 행도
        없이 역할이 사라진다 — API가 보장하는 두 가지가 동시에 무너진다."""
        from django.contrib import admin as django_admin

        from .models import UserRole as UserRoleModel

        model_admin = django_admin.site._registry[UserRoleModel]
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None))
        self.assertFalse(model_admin.has_delete_permission(None))



# ═══════════════════════════════════════════════════════════════════════════
# SPEC-005 / TASK-001 — 인증 회귀 기반 (#2·#3·#4·#7·#8·#9)
#
# 이 블록은 **이미 동작하는 것을 고정**한다. 구현은 바꾸지 않는다.
# 쓰는 도중 api.md 계약과 다른 동작이 네 곳에서 나왔다(F-1~F-4). 규칙대로
# 고치지 않고 분리 보고했으며, 계약을 단언하는 테스트는 `@expectedFailure`로
# 둔다. 스위트는 녹색을 유지하되, 누군가 고치는 순간 "예상치 못한 성공"으로
# 떠서 데코레이터를 떼라고 알려준다 — 결함을 잊지 않게 하는 래칫이다.
#
# 세션을 다루는 테스트는 force_authenticate를 쓰지 않는다. 그건 인증기를
# 통째로 건너뛰므로 세션 발급·삭제를 검증하지 못한다.
# ═══════════════════════════════════════════════════════════════════════════

SIGNUP_URL = "/api/v1/auth/signup"
LOGIN_URL = "/api/v1/auth/login"
LOGOUT_URL = "/api/v1/auth/logout"
ME_URL = "/api/v1/users/me"
MY_ROLES_URL = "/api/v1/users/me/roles"
STRONG_PW = "Strong-pass-123"


class AuthTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.existing = User.objects.create_user(
            email="alpha@example.com", nickname="alpha", password=STRONG_PW
        )

    def signup(self, **over):
        body = {"email": "new@example.com", "nickname": "newbie", "password": STRONG_PW}
        body.update(over)
        return self.client.post(SIGNUP_URL, body, format="json")

    def login(self, email="alpha@example.com", password=STRONG_PW, client=None):
        c = client or self.client
        return c.post(LOGIN_URL, {"email": email, "password": password}, format="json")


class SignupRegressionTests(AuthTestBase):
    """POST /api/v1/auth/signup (#2)."""

    def test_creates_account_and_returns_201(self):
        response = self.signup()
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    def test_response_fields_never_carry_the_password(self):
        response = self.signup()
        self.assertEqual(
            set(response.data),
            {"user_id", "email", "nickname", "active_role", "created_at"},
        )
        self.assertNotIn(STRONG_PW, response.content.decode())
        self.assertEqual(response.data["active_role"], "USER")

    def test_issues_an_httponly_session_cookie(self):
        """가입 즉시 로그인된다(CLAUDE.md §4 — Signup auto-logs in)."""
        response = self.signup()
        self.assertIn("sessionid", response.cookies)
        self.assertTrue(response.cookies["sessionid"]["httponly"])

    def test_signup_session_is_usable_immediately(self):
        self.signup()
        self.assertEqual(self.client.get(ME_URL).status_code, 200)

    def test_email_is_stored_lowercased(self):
        self.signup(email="Mixed@Example.COM")
        self.assertTrue(User.objects.filter(email="mixed@example.com").exists())

    def test_password_is_hashed_not_stored_plain(self):
        self.signup()
        user = User.objects.get(email="new@example.com")
        self.assertNotEqual(user.password, STRONG_PW)
        self.assertTrue(user.check_password(STRONG_PW))

    def test_weak_password_is_400(self):
        response = self.signup(password="1234")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data["error"]["details"])
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_duplicate_email_is_rejected(self):
        """현재 동작 고정: 거절은 된다(상태 코드는 F-2 참조)."""
        response = self.signup(email="alpha@example.com")
        self.assertIn(response.status_code, (400, 409))
        self.assertEqual(User.objects.filter(email="alpha@example.com").count(), 1)

    def test_duplicate_nickname_is_rejected(self):
        response = self.signup(nickname="alpha")
        self.assertIn(response.status_code, (400, 409))
        self.assertEqual(User.objects.filter(nickname="alpha").count(), 1)

    def test_duplicate_email_is_409_per_contract(self):
        """F-2 (TASK-006에서 수정). api.md #2는 중복을 409로 정한다."""
        response = self.signup(email="alpha@example.com")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["details"]["reason"], "EMAIL_TAKEN")

    def test_duplicate_nickname_is_409_per_contract(self):
        """F-2."""
        response = self.signup(nickname="alpha")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["details"]["reason"], "NICKNAME_TAKEN")

    def test_duplicate_email_in_other_case_is_409_not_500(self):
        """F-1 (결함). 중복 검사는 입력값 그대로(대소문자 구분) 비교하는데,
        저장 시 매니저가 소문자로 바꾼다 — 검사를 통과한 뒤 DB 제약에 걸려
        IntegrityError가 처리되지 않은 채 500이 된다. 사용자 입력으로 서버가
        죽는 경로다."""
        response = self.signup(email="ALPHA@example.com")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(User.objects.filter(email="alpha@example.com").count(), 1)

    def test_signup_race_past_the_checks_is_409_not_500(self):
        """중복 검사(SELECT)와 저장(INSERT) 사이에 같은 주소의 가입이 끼어들면
        검사는 통과하고 DB 유니크 인덱스에서 걸린다. 그 경합을 검사를 건너뛰는
        것으로 재현한다 — 결과가 500이면 F-1이 다른 길로 돌아온 것이다."""
        with (
            patch("accounts.serializers.SignupSerializer.validate_email", lambda self, v: v),
            patch("accounts.serializers.SignupSerializer.validate_nickname", lambda self, v: v),
        ):
            response = self.signup(email="alpha@example.com")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(User.objects.filter(email="alpha@example.com").count(), 1)

    def test_nickname_length_rules_still_apply(self):
        """409 처리를 위해 필드를 직접 선언하면서 모델의 길이 규칙(2~20자)을
        잃지 않았는지."""
        self.assertEqual(self.signup(nickname="a").status_code, 400)
        self.assertEqual(self.signup(nickname="a" * 21).status_code, 400)

    def test_requires_csrf(self):
        """익명 상태 변경 요청도 CSRF를 요구한다(ADR-002 §5). 뷰에
        csrf_protect를 명시했기 때문이며, 빠지면 이 테스트가 잡는다."""
        client = APIClient(enforce_csrf_checks=True)
        response = client.post(
            SIGNUP_URL,
            {"email": "c@example.com", "nickname": "csrfx", "password": STRONG_PW},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class LoginRegressionTests(AuthTestBase):
    """POST /api/v1/auth/login (#3)."""

    def test_valid_credentials_return_200_and_session(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertIn("sessionid", response.cookies)
        self.assertEqual(self.client.get(ME_URL).status_code, 200)

    def test_response_wraps_identity_under_user(self):
        response = self.login()
        self.assertEqual(set(response.data), {"user"})
        self.assertEqual(
            set(response.data["user"]), {"user_id", "email", "nickname", "active_role"}
        )

    def test_email_match_is_case_insensitive(self):
        self.assertEqual(self.login(email="ALPHA@Example.com").status_code, 200)

    def test_wrong_password_and_unknown_account_are_indistinguishable(self):
        """어느 쪽인지 구분되면 로그인 창이 가입 여부 조회 도구가 된다(§10)."""
        wrong = self.login(password="nope-nope-123")
        unknown = self.login(email="nobody@example.com", password="nope-nope-123")
        self.assertEqual(wrong.status_code, unknown.status_code)
        self.assertEqual(wrong.content, unknown.content)
        self.assertNotIn("sessionid", wrong.cookies)

    def test_inactive_account_cannot_log_in(self):
        """보안상 핵심 불변식. 상태 코드는 F-4 참조."""
        self.existing.is_active = False
        self.existing.save(update_fields=["is_active"])
        response = self.login()
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(self.client.get(ME_URL).status_code, 401)

    def test_wrong_credentials_are_401_per_contract(self):
        """F-3 (TASK-006에서 수정). api.md §1.8 '인증 필요/실패' = 401."""
        self.assertEqual(self.login(password="nope-nope-123").status_code, 401)

    def test_inactive_account_answer_is_identical_to_wrong_password(self):
        """F-4 (문서를 코드에 맞춤). 비활성 계정에 403을 따로 주면 '계정이 있고
        비밀번호도 맞다'가 샌다. 틀린 비밀번호와 바이트 단위로 같아야 한다."""
        wrong = self.login(password="nope-nope-123")
        self.existing.is_active = False
        self.existing.save(update_fields=["is_active"])
        inactive = self.login()
        self.assertEqual(inactive.status_code, wrong.status_code)
        self.assertEqual(inactive.content, wrong.content)

    def test_requires_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(self.login(client=client).status_code, 403)


class LogoutRegressionTests(AuthTestBase):
    """POST /api/v1/auth/logout (#4).

    §10: 로그아웃은 서버 세션 레코드를 지우고 쿠키도 지워야 한다 — 클라이언트
    쿠키 삭제에만 기대면 안 된다.
    """

    def test_logout_deletes_the_server_session_record(self):
        self.login()
        key = self.client.cookies["sessionid"].value
        self.assertTrue(Session.objects.filter(session_key=key).exists())

        response = self.client.post(LOGOUT_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"message": "로그아웃 되었습니다."})
        self.assertFalse(Session.objects.filter(session_key=key).exists())

    def test_logout_clears_the_cookie(self):
        self.login()
        response = self.client.post(LOGOUT_URL)
        cookie = response.cookies["sessionid"]
        self.assertEqual(cookie.value, "")
        self.assertEqual(str(cookie["max-age"]), "0")

    def test_old_cookie_is_useless_after_logout(self):
        """쿠키를 몰래 복사해 둔 사람이 있어도 로그아웃 뒤에는 못 쓴다 —
        서버에 레코드가 없기 때문이다."""
        self.login()
        stolen = self.client.cookies["sessionid"].value
        self.client.post(LOGOUT_URL)

        other = APIClient()
        other.cookies["sessionid"] = stolen
        self.assertEqual(other.get(ME_URL).status_code, 401)

    def test_anonymous_logout_is_401(self):
        self.assertEqual(self.client.post(LOGOUT_URL).status_code, 401)


class ProfileRegressionTests(AuthTestBase):
    """GET/PATCH /api/v1/users/me (#7·#8) and GET /users/me/roles (#9)."""

    def setUp(self):
        super().setUp()
        self.login()

    def test_me_fields(self):
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.data),
            {"user_id", "email", "nickname", "active_role", "roles", "created_at"},
        )
        self.assertEqual(response.data["roles"], ["USER"])

    def test_me_never_exposes_advisor_type_or_password(self):
        body = self.client.get(ME_URL).content.decode()
        self.assertNotIn("advisor_type", body)
        self.assertNotIn("password", body)

    def test_partial_update_changes_only_sent_fields(self):
        response = self.client.patch(ME_URL, {"job": "개발자"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.existing.refresh_from_db()
        self.assertEqual(self.existing.job, "개발자")
        self.assertEqual(self.existing.nickname, "alpha")

    def test_update_response_fields(self):
        response = self.client.patch(ME_URL, {"interest": "커리어"}, format="json")
        self.assertEqual(
            set(response.data), {"user_id", "email", "nickname", "updated_at"}
        )

    def test_email_cannot_be_changed_through_profile_update(self):
        self.client.patch(ME_URL, {"email": "hijack@example.com"}, format="json")
        self.existing.refresh_from_db()
        self.assertEqual(self.existing.email, "alpha@example.com")

    def test_duplicate_nickname_is_409(self):
        User.objects.create_user(email="b@example.com", nickname="taken", password=STRONG_PW)
        response = self.client.patch(ME_URL, {"nickname": "taken"}, format="json")
        self.assertEqual(response.status_code, 409)

    def test_short_nickname_is_400(self):
        response = self.client.patch(ME_URL, {"nickname": "a"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_roles_endpoint_fields_and_defaults(self):
        response = self.client.get(MY_ROLES_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"roles", "active_role", "advisor_status"})
        self.assertEqual(response.data["roles"], ["USER"])
        self.assertEqual(response.data["advisor_status"], "NONE")

    def test_anonymous_is_401_on_all_three(self):
        anon = APIClient()
        self.assertEqual(anon.get(ME_URL).status_code, 401)
        self.assertEqual(anon.patch(ME_URL, {"job": "x"}, format="json").status_code, 401)
        self.assertEqual(anon.get(MY_ROLES_URL).status_code, 401)



# ═══════════════════════════════════════════════════════════════════════════
# SPEC-005 / TASK-002 — Google OAuth 회귀 (#5·#6)
#
# 이 프로젝트에서 자동 테스트도 스모크도 없던 유일한 영역이다.
#
# mock 경계는 **네트워크**(`urllib.request.urlopen`)다. `accounts.oauth`의
# 함수를 mock하면 그 함수가 검증되지 않는다. 여기서는 구글이 돌려줄 응답
# 바이트만 가짜로 주고, 발급자·audience·이메일 인증 검증과 계정 연결/생성,
# 닉네임 산정은 전부 실제 코드가 실행한다. 예상하지 못한 주소를 부르면
# 즉시 실패하게 해서, 테스트가 조용히 실제 네트워크로 나가는 일을 막는다.
# ═══════════════════════════════════════════════════════════════════════════

AUTHORIZE_URL = "/api/v1/auth/google/authorize"
CALLBACK_URL = "/api/v1/auth/google/callback"
TEST_CLIENT_ID = "test-client.apps.googleusercontent.com"

GOOGLE_TEST_SETTINGS = {
    "GOOGLE_OAUTH_CLIENT_ID": TEST_CLIENT_ID,
    "GOOGLE_OAUTH_CLIENT_SECRET": "test-secret",
    "GOOGLE_OAUTH_REDIRECT_URI": "http://testserver/api/v1/auth/google/callback",
    "GOOGLE_OAUTH_SUCCESS_REDIRECT": "/after-login",
}


class _FakeResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _claims(**over):
    """tokeninfo가 돌려주는 정상 응답. 필요한 값만 덮어써서 실패 경우를 만든다."""
    base = {
        "iss": "https://accounts.google.com",
        "aud": TEST_CLIENT_ID,
        "sub": "google-sub-001",
        "email": "jiwon@example.com",
        "email_verified": "true",
        "name": "Jiwon Kim",
    }
    base.update(over)
    return base


class FakeGoogle:
    """`urlopen` 대체물. 주소로 분기해 구글 두 엔드포인트를 흉내 낸다.

    tokeninfo 주소(`…/tokeninfo`)가 토큰 주소(`…/token`)로 *시작*하므로
    tokeninfo를 먼저 판별해야 한다 — 순서를 바꾸면 모든 호출이 토큰 교환으로
    잘못 라우팅된다.
    """

    def __init__(self, claims=None, token_payload=None, token_error=None, info_error=None):
        self.claims = claims if claims is not None else _claims()
        self.token_payload = (
            token_payload if token_payload is not None else {"id_token": "fake.id.token"}
        )
        self.token_error = token_error
        self.info_error = info_error
        self.calls = []

    def __call__(self, req, timeout=None):
        url = getattr(req, "full_url", req)
        self.calls.append(url)
        if url.startswith(oauth.GOOGLE_TOKENINFO_URL):
            if self.info_error:
                raise self.info_error
            return _FakeResponse(self.claims)
        if url == oauth.GOOGLE_TOKEN_URL:
            if self.token_error:
                raise self.token_error
            return _FakeResponse(self.token_payload)
        raise AssertionError(f"예상하지 못한 네트워크 호출: {url}")


@override_settings(**GOOGLE_TEST_SETTINGS)
class GoogleAuthorizeRegressionTests(TestCase):
    """GET /api/v1/auth/google/authorize (#5)."""

    def test_redirects_to_google_with_required_params(self):
        response = APIClient().get(AUTHORIZE_URL)
        self.assertEqual(response.status_code, 302)
        location = response["Location"]
        self.assertTrue(location.startswith(oauth.GOOGLE_AUTHORIZE_URL))
        for part in (
            f"client_id={TEST_CLIENT_ID}",
            "response_type=code",
            "scope=openid+email+profile",
            "redirect_uri=",
            "state=",
        ):
            self.assertIn(part, location)

    def test_state_in_url_matches_httponly_cookie(self):
        """콜백은 URL의 state와 쿠키의 state를 대조한다(OAuth용 CSRF). 둘이
        같은 값으로 발급돼야 하고, 쿠키는 스크립트가 읽을 수 없어야 한다."""
        response = APIClient().get(AUTHORIZE_URL)
        cookie = response.cookies["oauth_state"]
        self.assertTrue(cookie["httponly"])
        state_in_url = re.search(r"state=([^&]+)", response["Location"]).group(1)
        self.assertEqual(state_in_url, cookie.value)

    def test_state_is_different_every_time(self):
        a = APIClient().get(AUTHORIZE_URL).cookies["oauth_state"].value
        b = APIClient().get(AUTHORIZE_URL).cookies["oauth_state"].value
        self.assertNotEqual(a, b)

    def test_does_not_create_a_session(self):
        response = APIClient().get(AUTHORIZE_URL)
        self.assertNotIn("sessionid", response.cookies)

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="", GOOGLE_OAUTH_CLIENT_SECRET="")
    def test_unconfigured_is_500(self):
        self.assertEqual(APIClient().get(AUTHORIZE_URL).status_code, 500)


@override_settings(**GOOGLE_TEST_SETTINGS)
class GoogleCallbackRegressionTests(TestCase):
    """GET /api/v1/auth/google/callback (#6)."""

    STATE = "state-abc"

    def local_account(self):
        """구글과 같은 이메일로 이미 가입해 둔 로컬(비밀번호) 계정."""
        return User.objects.create_user(
            email="jiwon@example.com", nickname="jiwon", password=STRONG_PW
        )

    def callback(self, fake=None, state=STATE, cookie_state=STATE, code="auth-code", **extra):
        client = APIClient()
        if cookie_state is not None:
            client.cookies["oauth_state"] = cookie_state
        params = {"code": code, **extra}
        if state is not None:
            params["state"] = state
        if code is None:
            params.pop("code")
        fake = fake or FakeGoogle()
        with patch("accounts.oauth.urllib.request.urlopen", fake):
            response = client.get(CALLBACK_URL, params)
        return client, response, fake

    # --- 정상 경로 -----------------------------------------------------------

    def test_new_user_is_created_logged_in_and_redirected(self):
        client, response, _ = self.callback()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/after-login")
        user = User.objects.get(email="jiwon@example.com")
        self.assertTrue(
            GoogleIdentity.objects.filter(user=user, google_sub="google-sub-001").exists()
        )
        self.assertEqual(client.get(ME_URL).status_code, 200)

    def test_new_google_user_has_no_usable_password(self):
        """비밀번호 없이 만들어진 계정이다 — 이메일/비밀번호 로그인은 막혀 있어야
        한다. (SPEC-005 결정 2: #46이 이 계정에 비밀번호를 설정할 수 있게 된다.)"""
        self.callback()
        self.assertFalse(User.objects.get(email="jiwon@example.com").has_usable_password())

    def test_callback_clears_the_state_cookie(self):
        _, response, _ = self.callback()
        self.assertEqual(response.cookies["oauth_state"].value, "")

    def test_the_verified_token_is_the_one_just_exchanged(self):
        """토큰 교환 → 검증이 실제로 이어져 있는지. 교환에서 받은 id_token이
        tokeninfo 호출에 그대로 실려야 한다."""
        _, _, fake = self.callback(fake=FakeGoogle(token_payload={"id_token": "tok-777"}))
        self.assertEqual(fake.calls[0], oauth.GOOGLE_TOKEN_URL)
        self.assertIn("id_token=tok-777", fake.calls[1])
        self.assertEqual(len(fake.calls), 2)

    def test_nickname_is_derived_from_google_name(self):
        """C-11. 닉네임은 구글 이름에서 만든다."""
        self.callback()
        self.assertEqual(User.objects.get(email="jiwon@example.com").nickname, "Jiwon Kim")

    def test_nickname_falls_back_to_email_local_part(self):
        self.callback(fake=FakeGoogle(claims=_claims(name="", email="zed@example.com")))
        self.assertEqual(User.objects.get(email="zed@example.com").nickname, "zed")

    def test_nickname_collision_gets_a_numeric_suffix(self):
        User.objects.create_user(
            email="other@example.com", nickname="Jiwon Kim", password=STRONG_PW
        )
        self.callback()
        nickname = User.objects.get(email="jiwon@example.com").nickname
        self.assertRegex(nickname, r"^Jiwon Kim_\d{4}$")
        self.assertLessEqual(len(nickname), 20)

    def test_known_google_account_logs_into_the_same_user(self):
        self.callback()
        before = User.objects.count()
        client, response, _ = self.callback()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), before)
        self.assertEqual(client.get(ME_URL).data["email"], "jiwon@example.com")

    def test_existing_local_account_is_linked_not_duplicated(self):
        """같은 (구글이 인증한) 이메일의 로컬 계정이 있으면 새로 만들지 않고
        그 계정에 연결한다 — 계정을 둘로 쪼개지 않는다(§10)."""
        local = self.local_account()
        self.callback()
        self.assertEqual(User.objects.filter(email="jiwon@example.com").count(), 1)
        self.assertTrue(GoogleIdentity.objects.filter(user=local).exists())
        local.refresh_from_db()
        # F-5 (TASK-006): 연결 순간 기존 비밀번호는 무효가 된다 — 아래 테스트 참조.
        self.assertFalse(local.has_usable_password())

    def test_linking_disables_the_preexisting_password_and_sessions(self):
        """F-5 사전 계정 탈취. 가입(#2)은 이메일 소유를 확인하지 않으므로, 남이
        피해자 주소로 먼저 로컬 계정을 만들어 둘 수 있다. 피해자가 구글로
        들어와 그 계정에 연결될 때 **그 사람의 비밀번호와 세션이 살아 있으면
        안 된다.** 진짜 주인은 #45로 비밀번호를 다시 만들 수 있다."""
        self.local_account()
        squatter = APIClient()
        squatter.post(
            LOGIN_URL, {"email": "jiwon@example.com", "password": STRONG_PW}, format="json"
        )
        self.assertEqual(squatter.get(ME_URL).status_code, 200)

        owner, response, _ = self.callback()

        self.assertEqual(response.status_code, 302)
        # 침입자가 요청하기 **전에** 센다. 401 자체는 Django 세션 해시만으로도
        # 나오고, 그 요청이 해시 불일치로 행을 지워버리기 때문이다(TASK-004 §11).
        self.assertEqual(len(sessions_of(User.objects.get(email="jiwon@example.com"))), 1)
        self.assertEqual(owner.get(ME_URL).status_code, 200)
        self.assertEqual(squatter.get(ME_URL).status_code, 401)
        relogin = APIClient().post(
            LOGIN_URL, {"email": "jiwon@example.com", "password": STRONG_PW}, format="json"
        )
        self.assertEqual(relogin.status_code, 401)

    def test_second_login_of_a_linked_account_keeps_its_password(self):
        """비밀번호 무효화는 **연결하는 그 순간** 한 번만이다. 연결 뒤 #46으로
        만든 비밀번호가 다음 구글 로그인마다 지워지면 안 된다."""
        local = self.local_account()
        self.callback()
        local.refresh_from_db()
        local.set_password("Made-later-789")
        local.save(update_fields=["password"])

        self.callback()

        local.refresh_from_db()
        self.assertTrue(local.check_password("Made-later-789"))

    def test_linking_matches_email_case_insensitively(self):
        local = self.local_account()
        self.callback(fake=FakeGoogle(claims=_claims(email="Jiwon@Example.COM")))
        self.assertTrue(GoogleIdentity.objects.filter(user=local).exists())
        self.assertEqual(User.objects.count(), 1)

    # --- 거절 경로 ------------------------------------------------------------

    def test_account_already_linked_to_another_google_account_is_409(self):
        local = self.local_account()
        GoogleIdentity.objects.create(
            user=local, google_sub="someone-else", email="jiwon@example.com"
        )
        client, response, _ = self.callback()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(GoogleIdentity.objects.filter(user=local).count(), 1)
        self.assertEqual(client.get(ME_URL).status_code, 401)

    def test_unverified_email_is_rejected(self):
        """구글이 인증하지 않은 이메일을 믿으면, 남의 이메일로 구글 계정을 만든
        사람이 그 이메일의 기존 로컬 계정에 연결돼 들어갈 수 있다 — 계정 탈취."""
        local = self.local_account()
        client, response, _ = self.callback(fake=FakeGoogle(claims=_claims(email_verified="false")))
        self.assertEqual(response.status_code, 401)
        self.assertFalse(GoogleIdentity.objects.filter(user=local).exists())
        self.assertEqual(client.get(ME_URL).status_code, 401)

    def test_token_minted_for_another_app_is_rejected(self):
        """audience 검증. 다른 앱용으로 발급된 토큰을 받아주면 그 앱이 사용자의
        토큰을 들고 우리 서비스에 로그인할 수 있다."""
        _, response, _ = self.callback(fake=FakeGoogle(claims=_claims(aud="other-app")))
        self.assertEqual(response.status_code, 401)
        self.assertFalse(User.objects.filter(email="jiwon@example.com").exists())

    def test_wrong_issuer_is_rejected(self):
        _, response, _ = self.callback(fake=FakeGoogle(claims=_claims(iss="https://evil.example.com")))
        self.assertEqual(response.status_code, 401)

    def test_missing_sub_is_rejected(self):
        _, response, _ = self.callback(fake=FakeGoogle(claims=_claims(sub="")))
        self.assertEqual(response.status_code, 401)

    def test_state_mismatch_is_400_and_never_calls_google(self):
        _, response, fake = self.callback(state="attacker-state")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(fake.calls, [])

    def test_missing_state_cookie_is_400(self):
        _, response, fake = self.callback(cookie_state=None)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(fake.calls, [])

    def test_missing_code_is_400(self):
        _, response, _ = self.callback(code=None)
        self.assertEqual(response.status_code, 400)

    def test_user_cancelled_consent_is_400(self):
        _, response, fake = self.callback(error="access_denied")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(fake.calls, [])

    def test_google_unreachable_is_502(self):
        _, response, _ = self.callback(fake=FakeGoogle(token_error=urllib.error.URLError("down")))
        self.assertEqual(response.status_code, 502)

    def test_tokeninfo_unreachable_is_502(self):
        _, response, _ = self.callback(fake=FakeGoogle(info_error=urllib.error.URLError("down")))
        self.assertEqual(response.status_code, 502)

    def test_token_response_without_id_token_is_502(self):
        _, response, _ = self.callback(fake=FakeGoogle(token_payload={"access_token": "x"}))
        self.assertEqual(response.status_code, 502)

    def test_inactive_linked_account_is_401(self):
        self.callback()
        User.objects.filter(email="jiwon@example.com").update(is_active=False)
        client, response, _ = self.callback()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(client.get(ME_URL).status_code, 401)

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="", GOOGLE_OAUTH_CLIENT_SECRET="")
    def test_unconfigured_is_500(self):
        _, response, _ = self.callback()
        self.assertEqual(response.status_code, 500)


# ═══════════════════════════════════════════════════════════════════════════
# SPEC-005 / TASK-003 — 비밀번호 재설정 요청 (#45)
#
# 이 엔드포인트의 핵심 계약은 "무엇을 하느냐"보다 "무엇을 알려주지 않느냐"다
# (ADR-008 §2). 가입·미가입·Google 전용·비활성 — 어느 경우든 응답 바이트가
# 같아야 하고, 차이는 메일함(`mail.outbox`)에만 나타나야 한다. 그래서
# 테스트는 응답끼리 서로 비교하고, 메일은 따로 센다.
# ═══════════════════════════════════════════════════════════════════════════

RESET_URL = "/api/v1/auth/password-reset"
GUNICORN_DEFAULT_TIMEOUT = 30  # Dockerfile CMD does not override --timeout
RESET_PAGE = "https://app.example.test/reset-password"
# S-5: 토큰은 `#` 뒤(fragment)에 싣는다 — 브라우저가 서버로 보내지 않는 부분이다.
RESET_LINK_RE = re.compile(re.escape(RESET_PAGE) + r"#uid=([\w-]+)&token=([\w-]+)")


@override_settings(PASSWORD_RESET_URL=RESET_PAGE)
class PasswordResetRequestTests(AuthTestBase):
    """POST /api/v1/auth/password-reset (#45)."""

    def request_reset(self, email, client=None):
        c = client or self.client
        return c.post(RESET_URL, {"email": email}, format="json")

    def make_google_only(self):
        # password=None → unusable password + Google 연결 = Google 로그인만 되는 계정.
        user = User.objects.create_user(email="gonly@example.com", nickname="gonly")
        GoogleIdentity.objects.create(user=user, google_sub="g-only", email=user.email)
        return user

    def test_password_disabled_account_without_google_gets_no_mail(self):
        """S-2. 비밀번호가 '사용 불가'라도 Google 연결이 없다면 관리자가 비밀번호
        로그인을 꺼 둔 계정이다. 메일함만으로 다시 열 수 있으면 그 조치가
        무력해진다. 응답은 똑같이 둔다."""
        User.objects.create_user(email="locked@example.com", nickname="locked")
        baseline = self.request_reset("nobody@example.com")
        response = self.request_reset("locked@example.com")
        self.assertEqual(response.status_code, baseline.status_code)
        self.assertEqual(response.content, baseline.content)
        self.assertEqual(len(mail.outbox), 0)

    def test_registered_email_is_200_and_sends_one_mail(self):
        response = self.request_reset("alpha@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["alpha@example.com"])

    def test_response_body_matches_contract(self):
        response = self.request_reset("alpha@example.com")
        self.assertEqual(response.json(), {"detail": "메일을 보냈습니다."})

    def test_unregistered_email_gets_byte_identical_response_and_no_mail(self):
        """AC-3 핵심. 상태 코드든 본문이든 쿠키든, 하나라도 다르면 이 API가
        '가입 여부 조회기'가 된다(CLAUDE.md §10)."""
        registered = self.request_reset("alpha@example.com")
        mail.outbox.clear()
        unregistered = self.request_reset("nobody@example.com")

        self.assertEqual(unregistered.status_code, registered.status_code)
        self.assertEqual(unregistered.content, registered.content)
        self.assertEqual(set(unregistered.cookies), set(registered.cookies))
        self.assertEqual(dict(unregistered.items()), dict(registered.items()))
        self.assertEqual(len(mail.outbox), 0)

    def test_email_is_matched_case_insensitively(self):
        """저장값은 매니저가 소문자로 만든다. 입력도 같은 형태로 맞춰 찾는다."""
        self.request_reset("ALPHA@Example.com")
        self.assertEqual(len(mail.outbox), 1)
        # 보내는 곳은 입력값이 아니라 **저장된** 주소다. 입력값으로 보내면
        # 유니코드 대소문자 충돌로 남의 링크를 받는 길이 열린다(CVE-2019-19844 유형).
        self.assertEqual(mail.outbox[0].to, [self.existing.email])

    def test_mail_carries_a_working_link(self):
        """링크가 '있다'에서 끝내지 않고 uid가 이 사용자를 가리키는지, 토큰이
        실제로 통과하는지까지 본다 — SPEC-003의 `target_url`처럼 옳아 보이지만
        아무도 눌러보지 않은 링크를 만들지 않기 위해서다."""
        self.request_reset("alpha@example.com")
        match = RESET_LINK_RE.search(mail.outbox[0].body)
        self.assertIsNotNone(match, mail.outbox[0].body)

        uid, token = match.groups()
        self.assertEqual(urlsafe_base64_decode(uid).decode(), str(self.existing.pk))
        self.assertTrue(default_token_generator.check_token(self.existing, token))

    def test_google_only_account_gets_a_different_mail_with_a_link(self):
        """결정 2(spec §7): Google 전용 계정도 토큰이 유효하면 비밀번호를 만들
        수 있으므로 링크를 함께 준다. 다만 본문에서 Google 계정임을 알린다."""
        self.make_google_only()
        local = self.request_reset("alpha@example.com")
        google = self.request_reset("gonly@example.com")

        self.assertEqual(google.status_code, local.status_code)
        self.assertEqual(google.content, local.content)

        local_mail, google_mail = mail.outbox
        self.assertIn("Google", google_mail.body)
        self.assertNotIn("Google", local_mail.body)
        self.assertIsNotNone(RESET_LINK_RE.search(google_mail.body))

    def test_inactive_account_gets_identical_response_and_no_mail(self):
        """비활성 계정은 새 비밀번호로도 로그인할 수 없다(#3). 메일을 보낼
        이유가 없고, Django 기본 재설정 폼도 같은 이유로 건너뛴다."""
        baseline = self.request_reset("nobody@example.com")
        User.objects.filter(pk=self.existing.pk).update(is_active=False)
        response = self.request_reset("alpha@example.com")

        self.assertEqual(response.status_code, baseline.status_code)
        self.assertEqual(response.content, baseline.content)
        self.assertEqual(len(mail.outbox), 0)

    def test_mail_failure_does_not_change_the_response(self):
        """메일 서버가 죽었을 때 가입된 주소에만 500이 나면, 그 500이 곧
        '가입됨' 신호다. 실패는 로그로만 남기고 응답은 같게 둔다. 로그에는
        주소가 아니라 pk만 남긴다(개인정보)."""
        baseline = self.request_reset("nobody@example.com")
        with (
            patch(
                "django.core.mail.backends.locmem.EmailBackend.send_messages",
                side_effect=ConnectionRefusedError("smtp down"),
            ),
            self.assertLogs("accounts.emails", level="ERROR") as logs,
        ):
            response = self.request_reset("alpha@example.com")

        self.assertEqual(response.status_code, baseline.status_code)
        self.assertEqual(response.content, baseline.content)
        self.assertNotIn("alpha@example.com", "\n".join(logs.output))

    def test_refused_recipient_log_does_not_carry_the_address(self):
        """보안 리뷰 S-4. SMTP가 수신자를 거부하면 예외 문자열 자체에 주소가
        들어 있다({'alpha@example.com': (550, ...)}). traceback을 통째로 남기면
        '주소는 남기지 않는다'가 실제 거부 상황에서 깨진다."""
        refused = smtplib.SMTPRecipientsRefused({"alpha@example.com": (550, b"no such user")})
        with (
            patch(
                "django.core.mail.backends.locmem.EmailBackend.send_messages",
                side_effect=refused,
            ),
            self.assertLogs("accounts.emails", level="ERROR") as logs,
        ):
            self.request_reset("alpha@example.com")

        self.assertNotIn("alpha@example.com", "\n".join(logs.output))
        self.assertIn("SMTPRecipientsRefused", "\n".join(logs.output))

    def test_mail_send_has_a_timeout_shorter_than_the_worker_timeout(self):
        """보안 리뷰 S-1. 타임아웃이 없으면(Django 기본 None) 응답 없는 메일
        서버 앞에서 gunicorn 워커(기본 30초)가 먼저 죽는다. 그 종료는
        SystemExit라 except Exception이 못 잡는다 — 가입된 주소에만 502가 나고
        (가입 여부 신호), 요청 몇 건으로 워커 전부가 묶인다."""
        self.assertIsNotNone(settings.EMAIL_TIMEOUT)
        self.assertLess(settings.EMAIL_TIMEOUT, GUNICORN_DEFAULT_TIMEOUT)

    def test_malformed_email_is_400(self):
        self.assertEqual(self.request_reset("not-an-email").status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_missing_email_is_400(self):
        self.assertEqual(self.client.post(RESET_URL, {}, format="json").status_code, 400)

    def test_requires_csrf(self):
        """익명 POST라도 상태를 바꾸는(메일을 보내는) 요청이다(ADR-002 §5)."""
        client = APIClient(enforce_csrf_checks=True)
        response = self.request_reset("alpha@example.com", client=client)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_passes_with_bootstrapped_csrf_token(self):
        """403 테스트의 짝. #44로 받은 토큰을 헤더에 실으면 통과해야 한다 —
        그래야 403이 'CSRF 때문'이라는 것이 증명된다."""
        client = APIClient(enforce_csrf_checks=True)
        client.get("/api/v1/csrf")
        token = client.cookies["csrftoken"].value
        response = client.post(
            RESET_URL, {"email": "alpha@example.com"}, format="json", HTTP_X_CSRFTOKEN=token
        )
        self.assertEqual(response.status_code, 200)

    def test_changes_nothing_in_the_database(self):
        """AC-3 '토큰이 DB에 저장되지 않는다'. Django 토큰은 비밀번호 해시와
        last_login으로 계산되므로 저장할 것이 없다. 세션도 만들지 않는다."""
        password_before = self.existing.password
        with CaptureQueriesContext(connection) as ctx:
            response = self.request_reset("alpha@example.com")

        self.assertEqual(response.status_code, 200)
        writes = [q["sql"] for q in ctx.captured_queries if not q["sql"].startswith("SELECT")]
        self.assertEqual(writes, [])
        self.assertNotIn("sessionid", response.cookies)
        self.existing.refresh_from_db()
        self.assertEqual(self.existing.password, password_before)

    def test_token_lifetime_is_30_minutes(self):
        self.assertEqual(settings.PASSWORD_RESET_TIMEOUT, 30 * 60)


# ═══════════════════════════════════════════════════════════════════════════
# SPEC-005 / TASK-004 — 비밀번호 재설정 확정 (#46)
#
# 토큰은 직접 만들지 않고 #45가 실제로 보낸 메일에서 꺼낸다. 두 엔드포인트가
# 같은 형식으로 말하는지까지 함께 검증하기 위해서다.
#
# 세션 무효화는 두 겹이다. ① Django는 세션에 비밀번호에서 파생한 해시를 넣어
# 두고 요청마다 대조하므로, 비밀번호가 바뀌면 옛 세션은 다음 요청에서 저절로
# 로그아웃된다. ② 그 위에 서비스가 그 사용자의 세션 행을 서버에서 지운다
# (#4 로그아웃과 같은 원칙, ADR-002 §4). ①만으로도 401이 나오므로, ②는 세션
# '행'이 사라졌는지로 따로 검증한다 — 그러지 않으면 ②를 지워도 아무 테스트도
# 실패하지 않는다.
#
# 만료는 PASSWORD_RESET_TIMEOUT=0이 아니라 발급 시각을 과거로 돌려 검증한다.
# Django의 만료 판정은 `>`라서 0초 설정은 같은 초 안에 만든 토큰을 통과시킨다
# (실행 타이밍에 따라 결과가 갈리는 테스트가 된다).
# ═══════════════════════════════════════════════════════════════════════════

CONFIRM_URL = "/api/v1/auth/password-reset/confirm"
NEW_PW = "Brand-new-pass-456"


def sessions_of(user):
    user_id = str(user.pk)
    return [s for s in Session.objects.all() if s.get_decoded().get(SESSION_KEY) == user_id]


@override_settings(PASSWORD_RESET_URL=RESET_PAGE)
class PasswordResetConfirmTests(AuthTestBase):
    """POST /api/v1/auth/password-reset/confirm (#46)."""

    def issue_link(self, email="alpha@example.com"):
        mail.outbox.clear()
        APIClient().post(RESET_URL, {"email": email}, format="json")
        return RESET_LINK_RE.search(mail.outbox[-1].body).groups()

    def issue_link_minutes_ago(self, minutes):
        issued_at = datetime.now() - timedelta(minutes=minutes)
        with patch.object(default_token_generator, "_now", return_value=issued_at):
            return self.issue_link()

    def confirm(self, uid, token, new_password=NEW_PW, client=None):
        c = client or APIClient()
        body = {"uid": uid, "token": token, "new_password": new_password}
        return c.post(CONFIRM_URL, body, format="json")

    def stored_password(self, user=None):
        return User.objects.get(pk=(user or self.existing).pk).password

    def assert_can_login(self, password, email="alpha@example.com"):
        self.assertEqual(
            self.login(email=email, password=password, client=APIClient()).status_code, 200
        )

    def assert_cannot_login(self, password, email="alpha@example.com"):
        # 200이 아니기만 하면 된다 — 실패 코드(400/401)는 F-3 결정에 달렸다.
        self.assertNotEqual(
            self.login(email=email, password=password, client=APIClient()).status_code, 200
        )

    # ── 성공 경로 ────────────────────────────────────────────────────────

    def test_valid_link_changes_the_password(self):
        response = self.confirm(*self.issue_link())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"detail": "비밀번호를 바꿨습니다."})
        self.assert_can_login(NEW_PW)
        self.assert_cannot_login(STRONG_PW)

    def test_confirm_does_not_log_the_caller_in(self):
        """재설정은 로그인이 아니다. 새 비밀번호로 #3을 거치게 한다."""
        client = APIClient()
        response = self.confirm(*self.issue_link(), client=client)
        self.assertNotIn("sessionid", response.cookies)
        self.assertEqual(client.get(ME_URL).status_code, 401)

    def test_token_is_still_valid_just_under_30_minutes(self):
        """만료 테스트의 짝 — 31분이 실패하는 이유가 '시간' 때문임을 보인다."""
        self.assertEqual(self.confirm(*self.issue_link_minutes_ago(29)).status_code, 200)

    def test_google_only_account_can_set_a_password(self):
        """결정 2(spec §7): 토큰을 가졌다는 것은 메일함 소유가 증명된 것이다."""
        google_only = User.objects.create_user(email="gonly@example.com", nickname="gonly")
        GoogleIdentity.objects.create(
            user=google_only, google_sub="g-only", email="gonly@example.com"
        )
        response = self.confirm(*self.issue_link("gonly@example.com"))
        self.assertEqual(response.status_code, 200)
        google_only.refresh_from_db()
        self.assertTrue(google_only.has_usable_password())
        self.assert_can_login(NEW_PW, email="gonly@example.com")

    # ── 실패 경로: 전부 400, 비밀번호 불변 ───────────────────────────────

    def test_reused_token_is_400_and_password_unchanged(self):
        uid, token = self.issue_link()
        self.assertEqual(self.confirm(uid, token).status_code, 200)
        after_first = self.stored_password()

        response = self.confirm(uid, token, new_password="Another-pass-789")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.stored_password(), after_first)
        self.assert_can_login(NEW_PW)

    def test_expired_token_is_400_and_password_unchanged(self):
        before = self.stored_password()
        response = self.confirm(*self.issue_link_minutes_ago(31))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.stored_password(), before)

    def test_forged_token_is_400_and_password_unchanged(self):
        before = self.stored_password()
        uid, token = self.issue_link()
        forged = token[:-1] + ("a" if token[-1] != "a" else "b")
        self.assertEqual(self.confirm(uid, forged).status_code, 400)
        self.assertEqual(self.stored_password(), before)

    def test_inactive_account_link_is_rejected(self):
        """#45가 비활성 계정에 메일을 보내지 않는 것(I-1)과 짝. 메일을 받은 뒤
        비활성화된 경우에도 링크가 통하면 안 된다."""
        uid, token = self.issue_link()
        User.objects.filter(pk=self.existing.pk).update(is_active=False)
        before = self.stored_password()
        self.assertEqual(self.confirm(uid, token).status_code, 400)
        self.assertEqual(self.stored_password(), before)

    def test_password_disabled_account_cannot_be_reopened(self):
        """S-2의 #46 쪽 방어. 메일이 안 나가도 토큰은 계산으로 만들 수 있으므로
        확정 단계에서도 같은 조건을 잠근 행으로 다시 본다."""
        locked = User.objects.create_user(email="locked@example.com", nickname="locked")
        uid = urlsafe_base64_encode(force_bytes(locked.pk))
        token = default_token_generator.make_token(locked)
        self.assertEqual(self.confirm(uid, token).status_code, 400)
        locked.refresh_from_db()
        self.assertFalse(locked.has_usable_password())

    def test_all_link_failures_are_indistinguishable(self):
        """AC-4 핵심. 만료·위조·재사용·없는 계정·깨진 uid를 구분해 주면 어떤
        토큰이나 계정이 '존재했다'는 정보가 샌다(api.md #46)."""
        uid, token = self.issue_link()
        unknown_uid = urlsafe_base64_encode(force_bytes(uuid.uuid4()))
        cases = {
            "expired": self.confirm(*self.issue_link_minutes_ago(31)),
            "forged": self.confirm(uid, token[:-1] + ("a" if token[-1] != "a" else "b")),
            "unknown uid": self.confirm(unknown_uid, token),
            "garbage uid": self.confirm("!!not-base64!!", token),
        }
        self.assertEqual(self.confirm(uid, token).status_code, 200)
        cases["reused"] = self.confirm(uid, token, new_password="Another-pass-789")

        self.assertEqual({r.status_code for r in cases.values()}, {400}, cases)
        self.assertEqual(len({r.content for r in cases.values()}), 1)

    def test_weak_password_is_400_and_does_not_burn_the_token(self):
        """검증기 4종(AUTH_PASSWORD_VALIDATORS)을 그대로 쓴다. 약한 비밀번호로
        실패해도 비밀번호가 안 바뀌었으니 같은 링크로 다시 시도할 수 있어야 한다."""
        uid, token = self.issue_link()
        before = self.stored_password()

        response = self.confirm(uid, token, new_password="123")
        self.assertEqual(response.status_code, 400)
        self.assertIn("new_password", response.json()["error"]["details"])
        self.assertEqual(self.stored_password(), before)

        self.assertEqual(self.confirm(uid, token).status_code, 200)

    def test_missing_fields_are_400(self):
        response = APIClient().post(CONFIRM_URL, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()["error"]["details"]), {"uid", "token", "new_password"})

    def test_requires_csrf(self):
        before = self.stored_password()
        response = self.confirm(*self.issue_link(), client=APIClient(enforce_csrf_checks=True))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.stored_password(), before)

    def test_error_report_does_not_carry_the_password_or_token(self):
        """보안 리뷰 #46 체크리스트 6. 운영(DEBUG=False)에서 500이 나면 Django
        오류 리포트(관리자 메일 등)가 request.POST와 각 프레임의 지역 변수를
        담는다 — 둘 다 가려야 한다. DEBUG=True 화면은 Django가 일부러 가리지
        않으므로(로컬 전용) 여기서는 리포트 자체를 만들어 확인한다."""
        uid, token = self.issue_link()
        reports = []

        def capture(sender, request, **kwargs):
            reports.append(ExceptionReporter(request, *sys.exc_info()).get_traceback_html())

        got_request_exception.connect(capture)
        try:
            # 세션 정리 단계에서 터뜨린다 — 그 위의 뷰·서비스 프레임 지역 변수에
            # 비밀번호와 토큰이 들어 있는 상태로 리포트가 만들어진다.
            with patch("accounts.services._purge_sessions_of", side_effect=RuntimeError("boom")):
                response = APIClient(raise_request_exception=False).post(
                    CONFIRM_URL, {"uid": uid, "token": token, "new_password": NEW_PW}
                )
        finally:
            got_request_exception.disconnect(capture)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(len(reports), 1)
        self.assertIn("boom", reports[0])  # 리포트가 실제로 그 오류를 담았다
        self.assertNotIn(NEW_PW, reports[0])
        self.assertNotIn(token, reports[0])

    # ── 세션 무효화 ──────────────────────────────────────────────────────

    def test_existing_sessions_of_that_user_are_logged_out(self):
        """비밀번호를 되찾는 상황 = 계정이 탈취됐을 수 있는 상황. 침입자의
        세션이 살아 있으면 비밀번호만 바뀌고 침입자는 그대로 남는다."""
        victim_device, intruder_device = APIClient(), APIClient()
        self.login(client=victim_device)
        self.login(client=intruder_device)

        self.confirm(*self.issue_link())

        self.assertEqual(victim_device.get(ME_URL).status_code, 401)
        self.assertEqual(intruder_device.get(ME_URL).status_code, 401)

    def test_server_side_session_rows_are_deleted_only_for_that_user(self):
        """spec §8 리스크 4: 해당 사용자의 세션만 지워야 한다."""
        other = User.objects.create_user(
            email="bravo@example.com", nickname="bravo", password=STRONG_PW
        )
        self.login(client=APIClient())
        self.login(client=APIClient())
        other_device = APIClient()
        self.login(email="bravo@example.com", client=other_device)
        self.assertEqual(len(sessions_of(self.existing)), 2)

        self.confirm(*self.issue_link())

        self.assertEqual(sessions_of(self.existing), [])
        self.assertEqual(len(sessions_of(other)), 1)
        self.assertEqual(other_device.get(ME_URL).status_code, 200)

    # ── 상태 전이 규칙(.claude/rules/coding.md) ──────────────────────────

    def test_locks_the_user_row_and_writes_only_the_password(self):
        """잠금이 없으면 같은 링크 두 번이 동시에 들어올 때 둘 다 토큰 검사를
        통과할 수 있다. 잠근 뒤 다시 읽어야 두 번째가 바뀐 비밀번호를 보고
        실패한다."""
        uid, token = self.issue_link()
        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(self.confirm(uid, token).status_code, 200)
        sqls = [q["sql"] for q in ctx.captured_queries]

        self.assertTrue(any('FOR UPDATE OF "accounts_user"' in s for s in sqls))
        updates = [s for s in sqls if s.startswith('UPDATE "accounts_user"')]
        self.assertEqual(len(updates), 1)
        set_clause = updates[0].split(" WHERE ")[0]
        self.assertIn('"password"', set_clause)
        self.assertIn('"updated_at"', set_clause)
        for column in ('"email"', '"nickname"', '"is_active"', '"last_login"', '"active_role"'):
            self.assertNotIn(column, set_clause)
