"""Notification service layer (model.md §5, api.md #39-#41).

Access control lives in the queryset, not in a post-fetch ownership check:
every lookup starts from `Notification.objects.filter(recipient=user)`, so a
notification addressed to someone else is never loaded and the view answers 404
(spec.md §7 결정 2). Fetching first and comparing owners afterwards is the shape
that produces 403/404 mix-ups, so it is deliberately not used here.
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Notification


def list_my_notifications(user, *, is_read=None, notification_type=None):
    """My notifications, newest first (#39).

    `-id` is a tiebreaker, not decoration: UUIDv7 is time-ordered, so two rows
    written in the same transaction still come back in a stable order.
    """
    queryset = Notification.objects.filter(recipient=user).order_by("-created_at", "-id")
    if is_read is not None:
        queryset = queryset.filter(is_read=is_read)
    if notification_type:
        queryset = queryset.filter(type=notification_type)
    return queryset


def unread_count(user) -> int:
    """Total unread notifications, deliberately ignoring the list filters —
    a badge number that changes when the user toggles a filter is wrong (#39).
    """
    return Notification.objects.filter(recipient=user, is_read=False).count()


def get_my_notification(user, notification_id) -> Notification:
    """One of *my* notifications, or 404 (#40)."""
    return get_object_or_404(
        Notification.objects.filter(recipient=user), pk=notification_id
    )


def mark_read(user, notification_id) -> Notification:
    """Mark one of my notifications read, idempotently (#41).

    Follows the state-transition rule in .claude/rules/coding.md: atomic +
    select_for_update(of=("self",)) + save(update_fields=[...]).

    `read_at` is written only on the first read. api.md #41 has no 409, so a
    repeat call must succeed — but succeeding by overwriting the timestamp
    would silently destroy "when the user first saw this", so the guard is on
    the write, not on the response.
    """
    with transaction.atomic():
        notification = get_object_or_404(
            Notification.objects.select_for_update(of=("self",)).filter(
                recipient=user
            ),
            pk=notification_id,
        )
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
    return notification
