"""Service layer for the advice API (SPEC-002, model.md §5).

Owns the rules a view must not inline: who may write an advice on which
concern, the one-active-advice-per-(concern, advisor) guarantee, and the
queryset shapes the list endpoints need.
"""

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404

from common.exceptions import Conflict
from concerns.models import Assignment, Concern

from .models import Advice, AdviceHistory, AdviceStatus

# States in which the author may still change or withdraw an advice
# (api.md #29/#30) — anything else (APPROVED/REJECTED/DELETED) is terminal
# for the author and returns 409.
_EDITABLE_STATUSES = (AdviceStatus.PENDING, AdviceStatus.REVIEWING)

# The body fields that make up an AdviceHistory snapshot (model.md §3.9).
# `is_submitted` is deliberately excluded — spec.md §7-2: it is a workflow
# flag, not part of the advice's body history, so toggling it alone must not
# create a snapshot or bump `version`.
_BODY_FIELDS = (
    "directional_guidance",
    "reflective_questions",
    "considerations",
    "out_of_scope_flag",
)


def create_advice(concern_id, advisor, validated_data) -> Advice:
    """#28 — write an advice on an assigned concern.

    404 for a missing or soft-deleted concern (the default manager hides
    soft-deleted rows), 403 when the advisor has no active assignment on it,
    409 when they already have a live advice there.

    No side effects: §6.4 defines no notification for authoring, and the
    concern only moves to ANSWERED once an advice is *approved* (§6.6).
    """
    concern = get_object_or_404(Concern.objects, pk=concern_id)
    if not Assignment.objects.filter(
        concern=concern, advisor=advisor, is_active=True
    ).exists():
        raise PermissionDenied("배정되지 않은 고민입니다.")

    # draft = PENDING + is_submitted=False (spec.md §4). Draft-ness is a flag,
    # never a status — the admin review queue filters on it (#32/#33).
    try:
        return Advice.objects.create(
            concern=concern,
            advisor=advisor,
            directional_guidance=validated_data["directional_guidance"],
            reflective_questions=validated_data.get("reflective_questions", ""),
            considerations=validated_data.get("considerations", ""),
            out_of_scope_flag=validated_data.get("out_of_scope_flag", False),
            is_submitted=validated_data["submit"],
        )
    except IntegrityError as exc:
        # The only unique constraint here is the (concern, advisor) partial
        # index excluding DELETED (model.md §3.8), so a withdrawn advice does
        # not block a rewrite.
        raise Conflict("이미 이 고민에 작성한 조언이 있습니다.") from exc


def list_advices_written_by(advisor):
    """Queryset for #31 — the advisor's own advices, every status, newest
    first. No derived fields, so no extra query beyond the page itself."""
    return Advice.objects.filter(advisor=advisor).order_by("-created_at")


# Viewer roles for #27 — the caller's relationship to the advice, not a model
# field. The view picks a serializer from this (author/admin see reject_reason,
# owner does not).
VIEWER_AUTHOR = "author"
VIEWER_OWNER = "owner"
VIEWER_ADMIN = "admin"


def _is_admin(user) -> bool:
    # Deliberately duplicates common.permissions.IsAdmin's check rather than
    # reusing the DRF permission class here: this is an object-level branch
    # inside a service function, not a view-level gate, and the two shapes
    # (has_permission(request, view) vs. a plain user) don't fit together
    # cleanly enough to be worth coupling them.
    if user.is_superuser:
        return True
    from accounts.models import Role, UserRole

    return UserRole.objects.filter(user=user, role=Role.ADMIN).exists()


def get_visible_advice(advice_id, user) -> tuple[Advice, str]:
    """#27 — fetch the target advice and decide which of the three shapes the
    caller may see (spec.md §7-4, CLAUDE.md §6.2).

    404 only for a genuinely missing advice. Existence is not hidden from a
    concern owner the way another user's *concern* is (SPEC-001 #18) — a
    non-APPROVED advice is 403 for them, matching api.md #27's own status
    list (Owner decision 2026-09-11).
    """
    advice = get_object_or_404(
        Advice.objects.select_related("concern", "advisor"), pk=advice_id
    )
    if advice.advisor_id == user.id:
        return advice, VIEWER_AUTHOR
    if _is_admin(user):
        return advice, VIEWER_ADMIN
    if advice.concern.author_id == user.id and advice.status == AdviceStatus.APPROVED:
        return advice, VIEWER_OWNER
    raise PermissionDenied("조회 권한이 없습니다.")


def _get_own_editable_advice(advice_id, actor) -> Advice:
    """Shared lookup for #29/#30: 404 if missing (existence is not hidden —
    same reasoning as #27), 403 if the caller didn't write it, 409 if its
    status is no longer editable (api.md #29/#30's own status-code sets)."""
    advice = get_object_or_404(Advice, pk=advice_id)
    if advice.advisor_id != actor.id:
        raise PermissionDenied("작성자만 수정할 수 있습니다.")
    if advice.status not in _EDITABLE_STATUSES:
        raise Conflict("현재 상태에서는 변경할 수 없습니다.")
    return advice


def update_advice(advice_id, actor, validated_data) -> Advice:
    """#29 — partial update. `version` increments, and a history row is
    snapshotted, only when a body field actually changes (Owner decision
    2026-09-11, spec.md §7-2) — a lone `submit` toggle does neither, since
    `version` is the body-history counter (CLAUDE.md §6.7).
    """
    advice = _get_own_editable_advice(advice_id, actor)

    body_changed = any(
        field in validated_data and getattr(advice, field) != validated_data[field]
        for field in _BODY_FIELDS
    )

    with transaction.atomic():
        if body_changed:
            # Snapshot the *pre-update* body under the *current* (soon to be
            # previous) version number (CLAUDE.md §6.7).
            AdviceHistory.objects.create(
                advice=advice,
                version=advice.version,
                edited_by=actor,
                **{field: getattr(advice, field) for field in _BODY_FIELDS},
            )
            advice.version += 1
        for field in _BODY_FIELDS:
            if field in validated_data:
                setattr(advice, field, validated_data[field])
        if "is_submitted" in validated_data:
            advice.is_submitted = validated_data["is_submitted"]
        advice.save()
    return advice


def delete_advice(advice_id, actor) -> None:
    """#30 — soft delete: status -> DELETED, nothing else. The row stays (the
    partial unique on (concern, advisor) excludes DELETED, model.md §3.8, so
    this deliberately does not block the advisor from writing a fresh advice
    on the same concern)."""
    advice = _get_own_editable_advice(advice_id, actor)
    advice.status = AdviceStatus.DELETED
    advice.save(update_fields=["status"])
