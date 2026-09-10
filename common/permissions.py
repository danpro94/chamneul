from rest_framework.permissions import BasePermission


class IsActiveAdvisor(BasePermission):
    """Grants access only when the user's *active* role is ADVISOR (api.md
    #20/#21; CLAUDE.md §2 Roles — "활성 역할을 ADVISOR로 전환하면 배정 고민
    조회 가능"). Holding the ADVISOR role without switching into it is not
    enough — that is a deliberate 403, not an oversight.
    """

    message = "조언가 역할로 전환한 상태에서만 접근할 수 있습니다."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        # Local import: mirrors IsAdmin below (avoid a load cycle).
        from accounts.models import ActiveRole

        return user.active_role == ActiveRole.ADVISOR


class IsAdmin(BasePermission):
    """Grants access only to ADMIN. A superuser is an ADMIN by definition
    (ADR-003 §1), and the createsuperuser hook also writes the ADMIN UserRole
    row — either signal is accepted so a bootstrap superuser is never locked out.
    """

    message = "관리자 권한이 필요합니다."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        # Local import: accounts imports common in places, avoid a load cycle.
        from accounts.models import Role, UserRole

        return UserRole.objects.filter(user=user, role=Role.ADMIN).exists()
