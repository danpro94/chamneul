"""Service layer for the concerns API (SPEC-001, model.md §5).

Owns query construction and state changes the view must not inline: creating
a concern, building the "my concerns" list queryset, fetching a single owned
concern (#18/#19), the soft-delete transition (#19, CLAUDE.md §6.6), and the
advisor-side assigned-concern queries (#20/#21).
"""

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Count, Exists, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404
from django.utils import timezone

from advice.models import Advice, AdviceStatus
from advisors.models import AdvisorApplication, AdvisorApplicationStatus
from common.exceptions import Conflict, UnprocessableEntity

from .models import Assignment, Concern, ConcernStatus


def create_concern(author, validated_data) -> Concern:
    """Create a concern. No side effects: initial status is SUBMITTED (model
    default) and no notification/state transition is triggered on creation."""
    return Concern.objects.create(author=author, **validated_data)


def list_my_concerns(user):
    """Queryset for #17 — the caller's own, non-deleted concerns (the default
    manager already filters deleted_at, CLAUDE.md §6.6), newest first,
    annotated with has_approved_advice (api.md #17 response field).
    """
    return (
        Concern.objects.filter(author=user)
        .annotate(
            has_approved_advice=Exists(
                Advice.objects.filter(concern=OuterRef("pk"), status=AdviceStatus.APPROVED)
            )
        )
        .order_by("-created_at")
    )


def get_own_concern(user, concern_id) -> Concern:
    """Fetch the target concern for #18 — 404 for missing, not-owned, *and*
    soft-deleted rows (the default manager hides deleted_at, so a deleted
    concern simply isn't found — matches spec.md #18: soft-deleted -> 404).
    """
    return get_object_or_404(Concern.objects.filter(author=user), pk=concern_id)


def get_own_concern_including_deleted(user, concern_id) -> Concern:
    """Fetch the target concern for #19 — includes already-deleted rows so a
    second delete attempt can be told 409 (already deleted) rather than 404.
    Still 404 for missing/not-owned (CLAUDE.md §10 object-level access control).
    """
    return get_object_or_404(Concern.objects.with_deleted().filter(author=user), pk=concern_id)


def soft_delete_concern(concern: Concern) -> None:
    """#19 — soft delete (CLAUDE.md §6.6): set deleted_at, nothing else.
    Advice/Assignment rows are untouched (audit trail preserved)."""
    if concern.deleted_at is not None:
        raise Conflict("이미 삭제된 고민입니다.")
    concern.deleted_at = timezone.now()
    concern.save(update_fields=["deleted_at"])


def display_names_by_advisor(advisor_ids) -> dict:
    """Bulk-resolve advisor display names: each advisor's most recent APPROVED
    advisor application (model.md §3.5). One query for any number of advisors
    — callers fall back to the account nickname for ids missing here (the rare
    admin-granted-without-application path, ADR-003 §2).
    """
    return dict(
        AdvisorApplication.objects.filter(
            applicant_id__in=advisor_ids, status=AdvisorApplicationStatus.APPROVED
        )
        .order_by("applicant_id", "-submitted_at")
        .distinct("applicant_id")
        .values_list("applicant_id", "display_name")
    )


def approved_advices_view_data(concern: Concern) -> list[dict]:
    """api.md #18 `approved_advices[]` — APPROVED-only exposure (CLAUDE.md
    §6.2). `advisor_display_name` is resolved in one bulk query, not per
    advice, to avoid N+1 (CLAUDE.md §8).
    """
    advices = list(
        Advice.objects.filter(concern=concern, status=AdviceStatus.APPROVED)
        .select_related("advisor")
        .order_by("created_at")
    )
    display_name_by_advisor = display_names_by_advisor(
        [advice.advisor_id for advice in advices]
    )
    return [
        {
            # str(): matches how every other id field in this API renders
            # (a DRF UUIDField's to_representation) — this dict bypasses that,
            # so it must convert explicitly (response.data would otherwise
            # carry a raw UUID object instead of the JSON string clients get).
            "advice_id": str(advice.id),
            "advisor_display_name": display_name_by_advisor.get(
                advice.advisor_id, advice.advisor.nickname
            ),
            "created_at": advice.created_at,
        }
        for advice in advices
    ]


def list_assigned_concerns(advisor):
    """Queryset for #20 — the advisor's own active assignments, newest first,
    annotated with `advice_status`: the advisor's own (non-deleted) advice
    status for that concern, or null if they haven't written one yet. A
    correlated Subquery keeps this to one query regardless of list size
    (CLAUDE.md §8 — avoid N+1).
    """
    own_advice_status = (
        Advice.objects.filter(concern=OuterRef("concern_id"), advisor=advisor)
        .exclude(status=AdviceStatus.DELETED)
        .order_by("-created_at")
        .values("status")[:1]
    )
    return (
        Assignment.objects.filter(advisor=advisor, is_active=True)
        .select_related("concern")
        .annotate(advice_status=Subquery(own_advice_status))
        .order_by("-assigned_at")
    )


def get_assigned_concern(advisor, concern_id):
    """Fetch the target concern for #21 — 404 if the concern doesn't exist
    (or is soft-deleted), 403 if it exists but isn't assigned to this advisor
    (api.md #21: existence is not hidden the way an unrelated user's concern
    is — CLAUDE.md §10's "don't reveal existence" applies to *ownership*,
    not to an advisor's assignment queue).
    """
    concern = get_object_or_404(Concern.objects, pk=concern_id)
    assignment = Assignment.objects.filter(
        concern=concern, advisor=advisor, is_active=True
    ).first()
    if assignment is None:
        raise PermissionDenied("배정되지 않은 고민입니다.")
    return concern, assignment


def requester_display_name(concern: Concern) -> str:
    """api.md #21 `requester_display_name` derivation (D-2, UX C-6/C-7):
    display_alias if set, else an anonymous placeholder or the account
    nickname depending on is_anonymous. Never the requester's email/user_id.
    """
    if concern.display_alias:
        return concern.display_alias
    if concern.is_anonymous:
        return "익명의 요청자"
    return concern.author.nickname


def my_advice_view_data(concern: Concern, advisor) -> dict | None:
    """api.md #21 `my_advice` — the advisor's own (non-deleted) advice on
    this concern, or None if they haven't written one."""
    advice = (
        Advice.objects.filter(concern=concern, advisor=advisor)
        .exclude(status=AdviceStatus.DELETED)
        .order_by("-created_at")
        .first()
    )
    if advice is None:
        return None
    return {
        "advice_id": str(advice.id),
        "status": advice.status,
        "version": advice.version,
        "is_submitted": advice.is_submitted,
    }


def assigned_concern_detail_view_data(concern: Concern, assignment: Assignment, advisor) -> dict:
    """api.md #21 full response payload — mixes Concern fields with the
    caller's own Assignment/Advice context, so it is assembled here rather
    than through a single ModelSerializer."""
    return {
        "concern_id": str(concern.id),
        "concern_summary": concern.concern_summary,
        "concern_type": concern.concern_type,
        "concern_type_secondary": concern.concern_type_secondary,
        "decision_context": concern.decision_context,
        "is_anonymous": concern.is_anonymous,
        "requester_display_name": requester_display_name(concern),
        "assigned_at": assignment.assigned_at,
        "assignment_id": str(assignment.id),
        "my_advice": my_advice_view_data(concern, advisor),
    }


def list_concerns_for_admin(include_deleted: bool = False):
    """Queryset for #22 — every user's concerns, newest first, annotated with
    `assignment_count`.

    `include_deleted` opts into soft-deleted rows via the unfiltered manager
    (CLAUDE.md §6.6: admin/audit access is the only path that sees them).
    assignment_count counts *active* assignments only — the useful operator
    signal is "how many advisors are working on this now", and deactivated
    rows are still visible in full on the #23 detail.
    """
    base = Concern.objects.with_deleted() if include_deleted else Concern.objects.all()
    return base.annotate(
        assignment_count=Count("assignments", filter=Q(assignments__is_active=True))
    ).order_by("-created_at")


def get_concern_for_admin(concern_id) -> Concern:
    """Fetch the target concern for #23 — includes soft-deleted rows, so a row
    surfaced by #22's include_deleted=true is actually reachable here."""
    return get_object_or_404(Concern.objects.with_deleted(), pk=concern_id)


def admin_concern_detail_view_data(concern: Concern) -> dict:
    """api.md #23 payload — the concern plus *every* assignment and advice
    regardless of state. CLAUDE.md §6.2's APPROVED-only rule protects concern
    owners (#18), not admins: review requires seeing PENDING/REJECTED too.

    Query budget is fixed (assignments + advices + one bulk display-name
    lookup), independent of row count (CLAUDE.md §8).
    """
    assignments = list(
        Assignment.objects.filter(concern=concern)
        .select_related("advisor")
        .order_by("-assigned_at")
    )
    advices = list(
        Advice.objects.filter(concern=concern).select_related("advisor").order_by("created_at")
    )
    display_name_by_advisor = display_names_by_advisor(
        [assignment.advisor_id for assignment in assignments]
    )
    return {
        "concern_id": str(concern.id),
        "author_user_id": str(concern.author_id),
        "concern_summary": concern.concern_summary,
        "concern_type": concern.concern_type,
        "concern_type_secondary": concern.concern_type_secondary,
        "preferred_advisor_lane": concern.preferred_advisor_lane,
        "decision_context": concern.decision_context,
        "display_alias": concern.display_alias,
        "is_anonymous": concern.is_anonymous,
        "status": concern.status,
        "is_deleted": concern.deleted_at is not None,
        "created_at": concern.created_at,
        "updated_at": concern.updated_at,
        "assignments": [
            {
                "assignment_id": str(assignment.id),
                "advisor_user_id": str(assignment.advisor_id),
                "advisor_display_name": display_name_by_advisor.get(
                    assignment.advisor_id, assignment.advisor.nickname
                ),
                "assigned_at": assignment.assigned_at,
                "assigned_by": str(assignment.assigned_by_id),
                "is_active": assignment.is_active,
            }
            for assignment in assignments
        ],
        "advices": [
            {
                "advice_id": str(advice.id),
                "advisor_user_id": str(advice.advisor_id),
                "status": advice.status,
                "version": advice.version,
                "created_at": advice.created_at,
            }
            for advice in advices
        ],
    }


def assign_advisor(concern_id, actor, validated_data) -> tuple[Assignment, Concern]:
    """#24 — attach an advisor to a concern, atomically (api.md #24).

    One transaction covers all three effects, so a failure can never leave an
    assignment without its state transition or its notification (CLAUDE.md
    §6.4/§6.6):
      1. Assignment row
      2. concern.status SUBMITTED -> ASSIGNED (only from SUBMITTED)
      3. ASSIGNMENT_CREATED notification to the advisor

    409 for a CLOSED/soft-deleted concern or a duplicate active assignment;
    422 when advisor_user_id is well-formed but not an ADVISOR.
    """
    # Deferred imports: accounts/notifications reference this app's models via
    # settings.AUTH_USER_MODEL strings; importing them at module load would
    # create a cycle (same pattern as advisors/services.py).
    from accounts.models import Role, UserRole
    from notifications.models import Notification, NotificationType

    advisor_user_id = validated_data["advisor_user_id"]
    if not UserRole.objects.filter(user_id=advisor_user_id, role=Role.ADVISOR).exists():
        # Well-formed id, unusable value -> 422 (api.md §1.8). Deliberately the
        # same answer whether the user is missing or simply not an advisor:
        # an admin tool must not double as a user-existence oracle.
        raise UnprocessableEntity("조언가 역할을 보유한 사용자가 아닙니다.")

    with transaction.atomic():
        # Lock the concern row: assign/unassign are read-modify-write on
        # concern.status, so concurrent admins must serialize here.
        concern = get_object_or_404(
            Concern.objects.with_deleted().select_for_update(), pk=concern_id
        )
        if concern.deleted_at is not None:
            raise Conflict("삭제된 고민에는 배정할 수 없습니다.")
        if concern.status == ConcernStatus.CLOSED:
            raise Conflict("종료된 고민에는 배정할 수 없습니다.")

        try:
            assignment = Assignment.objects.create(
                concern=concern,
                advisor_id=advisor_user_id,
                assigned_by=actor,
                triage_decision=validated_data["triage_decision"],
                match_rationale=validated_data.get("match_rationale") or {},
                priority=validated_data["priority"],
            )
        except IntegrityError as exc:
            # The only unique constraint here is the active (concern, advisor)
            # partial index (model.md §3.7).
            raise Conflict("이미 배정된 조언가입니다.") from exc

        if concern.status == ConcernStatus.SUBMITTED:
            concern.status = ConcernStatus.ASSIGNED
            concern.save(update_fields=["status"])

        Notification.objects.create(
            recipient_id=advisor_user_id,
            type=NotificationType.ASSIGNMENT_CREATED,
            title="새로운 고민이 배정되었습니다",
            message=concern.concern_summary,
            target_url=f"/api/v1/users/me/assigned-concerns/{concern.id}",
            actor_user=actor,
            payload={"concern_id": str(concern.id), "assignment_id": str(assignment.id)},
        )
    return assignment, concern


def unassign_advisor(concern_id, assignment_id) -> None:
    """#25 — deactivate an assignment, atomically (api.md #25).

    The row is never deleted: assignment history is itself audit (model.md
    §3.7). When the last active assignment goes, an ASSIGNED concern falls
    back to SUBMITTED (CLAUDE.md §6.6) — but an ANSWERED concern does not,
    because an approved advice already exists on it.
    """
    with transaction.atomic():
        concern = get_object_or_404(
            Concern.objects.with_deleted().select_for_update(), pk=concern_id
        )
        # Scoped to this concern: an assignment id from another concern is 404,
        # not a cross-concern write.
        assignment = get_object_or_404(Assignment, pk=assignment_id, concern=concern)
        if not assignment.is_active:
            raise Conflict("이미 해제된 배정입니다.")

        assignment.is_active = False
        assignment.deactivated_at = timezone.now()
        assignment.save(update_fields=["is_active", "deactivated_at"])

        still_assigned = Assignment.objects.filter(concern=concern, is_active=True).exists()
        if not still_assigned and concern.status == ConcernStatus.ASSIGNED:
            concern.status = ConcernStatus.SUBMITTED
            concern.save(update_fields=["status"])
