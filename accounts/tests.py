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

from notifications.models import Notification

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
