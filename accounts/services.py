"""Account service layer (model.md §5).

Role logic lives here (not in serializers/views) because it is a business rule
shared across M4-2 (active-role switch), M4-4 (advisor approval grants ADVISOR),
and M4-8 (admin grant/revoke). USER is the implicit default every account holds;
only ADVISOR/ADMIN are stored as UserRole rows (model.md §3.2).
"""

from rest_framework.exceptions import PermissionDenied

from .models import Role, UserRole

# advisor_status exposes only these (api.md #9). WITHDRAWN is unreachable in
# Phase 2 and maps to NONE if it somehow appears.
_ADVISOR_STATUSES = {"PENDING", "REVIEWING", "APPROVED", "REJECTED"}


def held_roles(user) -> list[str]:
    """Roles the user holds, USER first. USER is implicit (no row); ADVISOR/ADMIN
    come from UserRole. Order is stable (USER, ADVISOR, ADMIN) for UI rendering.
    """
    stored = set(UserRole.objects.filter(user=user).values_list("role", flat=True))
    roles = ["USER"]
    for role in (Role.ADVISOR, Role.ADMIN):
        if role in stored:
            roles.append(role)
    return roles


def advisor_status(user) -> str:
    """Latest advisor application status, or NONE (api.md #9)."""
    # Local import avoids an accounts -> advisors module dependency at load time.
    from advisors.models import AdvisorApplication

    app = (
        AdvisorApplication.objects.filter(applicant=user)
        .order_by("-submitted_at")
        .first()
    )
    if app is None or app.status not in _ADVISOR_STATUSES:
        return "NONE"
    return app.status


def set_active_role(user, target: str) -> None:
    """Switch active_role to a role the user actually holds (model.md §5).

    Raises PermissionDenied (403) if the target is not held. ADMIN is rejected
    upstream by the serializer's choices, so only USER/ADVISOR reach here.
    """
    if target not in held_roles(user):
        raise PermissionDenied("보유하지 않은 역할로는 전환할 수 없습니다.")
    user.active_role = target
    user.save(update_fields=["active_role", "updated_at"])
