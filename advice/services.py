"""Service layer for the advice API (SPEC-002, model.md §5).

Owns the rules a view must not inline: who may write an advice on which
concern, the one-active-advice-per-(concern, advisor) guarantee, and the
queryset shapes the list endpoints need.
"""

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.shortcuts import get_object_or_404

from common.exceptions import Conflict
from concerns.models import Assignment, Concern

from .models import Advice


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
