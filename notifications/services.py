"""Notification service layer (model.md §5, api.md #39-#41).

Access control lives in the queryset, not in a post-fetch ownership check:
every lookup starts from `Notification.objects.filter(recipient=user)`, so a
notification addressed to someone else is never loaded and the view answers 404
(spec.md §7 결정 2). Fetching first and comparing owners afterwards is the shape
that produces 403/404 mix-ups, so it is deliberately not used here.
"""

from django.shortcuts import get_object_or_404

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
