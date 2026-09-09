"""Advisor-application service layer (model.md §5).

Owns the two business actions the views must not inline: creating an application
(one active application per user) and reviewing it (state machine + approval side
effects). Approval is atomic — role grant, audit row, and notification either all
land or none do (the "role-less approved advisor" failure class from M2).
"""

from django.db import IntegrityError, transaction
from django.utils import timezone

from common.exceptions import Conflict, UnprocessableEntity

from .models import AdvisorApplication, AdvisorApplicationStatus

# Statuses that count as "in progress" — a user may not open a second
# application while one of these exists (api.md #11).
_ACTIVE_STATUSES = (
    AdvisorApplicationStatus.PENDING,
    AdvisorApplicationStatus.REVIEWING,
    AdvisorApplicationStatus.APPROVED,
)

# Allowed review transitions (api.md #15 / model.md §3.5). Terminal states
# (APPROVED/REJECTED/WITHDRAWN) have no outgoing edge -> re-transition is 409.
_ALLOWED_TRANSITIONS = {
    AdvisorApplicationStatus.PENDING: {AdvisorApplicationStatus.REVIEWING},
    AdvisorApplicationStatus.REVIEWING: {
        AdvisorApplicationStatus.APPROVED,
        AdvisorApplicationStatus.REJECTED,
    },
}


def create_application(applicant, validated_data) -> AdvisorApplication:
    """Create an application, rejecting a second in-progress one (409) and a
    display_name already taken by an active application (409, partial-unique)."""
    if AdvisorApplication.objects.filter(
        applicant=applicant, status__in=_ACTIVE_STATUSES
    ).exists():
        raise Conflict("이미 진행 중인 조언가 신청이 있습니다.")
    try:
        return AdvisorApplication.objects.create(applicant=applicant, **validated_data)
    except IntegrityError as exc:
        # The only unique constraint here is the active display_name partial index.
        raise Conflict("이미 사용 중인 활동명입니다.") from exc


def review_application(application, actor, target_status, reject_reason=""):
    """Apply a review transition and its side effects, atomically (api.md #15).

    APPROVED -> grant ADVISOR role + RoleGrant audit + applicant notification.
    REJECTED -> applicant notification (reason required, 422 if missing).
    """
    allowed = _ALLOWED_TRANSITIONS.get(application.status, set())
    if target_status not in allowed:
        raise Conflict(
            f"{application.status} 상태에서 {target_status}로 전이할 수 없습니다."
        )
    if target_status == AdvisorApplicationStatus.REJECTED and not reject_reason.strip():
        raise UnprocessableEntity("반려 시 사유는 필수입니다.")

    # Deferred imports keep advisors independent of accounts/notifications at
    # module load (they reference accounts via settings.AUTH_USER_MODEL strings).
    from accounts.models import Role, RoleGrant, RoleGrantAction, UserRole
    from notifications.models import Notification, NotificationType

    with transaction.atomic():
        application.status = target_status
        application.reviewed_by = actor
        application.reviewed_at = timezone.now()
        if target_status == AdvisorApplicationStatus.REJECTED:
            application.reject_reason = reject_reason
        application.save(
            update_fields=["status", "reviewed_by", "reviewed_at", "reject_reason"]
        )

        applicant = application.applicant
        if target_status == AdvisorApplicationStatus.APPROVED:
            # get_or_create: approving is idempotent w.r.t. an already-held role,
            # but a fresh grant always writes an audit row.
            UserRole.objects.get_or_create(user=applicant, role=Role.ADVISOR)
            RoleGrant.objects.create(
                user=applicant,
                role=Role.ADVISOR,
                action=RoleGrantAction.GRANT,
                acted_by=actor,
                reason="advisor application approved",
            )
            Notification.objects.create(
                recipient=applicant,
                type=NotificationType.ADVISOR_APPLICATION_APPROVED,
                title="조언가 신청이 승인되었습니다",
                message="조언가 역할이 부여되었습니다. 역할 전환 후 활동할 수 있어요.",
                target_url="/api/v1/advisor-applications/me",
                actor_user=actor,
                payload={"application_id": str(application.id)},
            )
        else:  # REJECTED
            Notification.objects.create(
                recipient=applicant,
                type=NotificationType.ADVISOR_APPLICATION_REJECTED,
                title="조언가 신청이 반려되었습니다",
                message=reject_reason,
                target_url="/api/v1/advisor-applications/me",
                actor_user=actor,
                payload={"application_id": str(application.id)},
            )
    return application
