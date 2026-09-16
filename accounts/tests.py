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

from django.contrib.auth import get_user_model
from django.test import TestCase
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

from .models import ActiveRole, Role, RoleGrant, RoleGrantAction, UserRole

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
