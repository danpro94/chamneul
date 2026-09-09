from rest_framework.permissions import BasePermission


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
