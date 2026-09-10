"""Service layer for the concerns API (SPEC-001, model.md §5).

Owns query construction and state changes the view must not inline: creating
a concern, building the "my concerns" list queryset, fetching a single owned
concern (#18/#19), and the soft-delete transition (#19, CLAUDE.md §6.6).
"""

from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404
from django.utils import timezone

from advice.models import Advice, AdviceStatus
from advisors.models import AdvisorApplication, AdvisorApplicationStatus
from common.exceptions import Conflict

from .models import Concern


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


def approved_advices_view_data(concern: Concern) -> list[dict]:
    """api.md #18 `approved_advices[]` — APPROVED-only exposure (CLAUDE.md
    §6.2). `advisor_display_name` comes from each advisor's most recent
    APPROVED advisor application (falls back to their account nickname for
    the rare admin-granted-without-application path, ADR-003 §2). Resolved
    in one extra query (not per-advice) to avoid N+1 (CLAUDE.md §8).
    """
    advices = list(
        Advice.objects.filter(concern=concern, status=AdviceStatus.APPROVED)
        .select_related("advisor")
        .order_by("created_at")
    )
    advisor_ids = [advice.advisor_id for advice in advices]
    display_name_by_advisor = dict(
        AdvisorApplication.objects.filter(
            applicant_id__in=advisor_ids, status=AdvisorApplicationStatus.APPROVED
        )
        .order_by("applicant_id", "-submitted_at")
        .distinct("applicant_id")
        .values_list("applicant_id", "display_name")
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
