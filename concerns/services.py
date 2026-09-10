"""Service layer for the concerns API (SPEC-001, model.md §5).

Owns query construction the view must not inline: creating a concern, and
building the "my concerns" list queryset with its has_approved_advice
annotation (kept here, not in the serializer, so it stays testable without a
request/view context).
"""

from django.db.models import Exists, OuterRef

from advice.models import Advice, AdviceStatus

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
