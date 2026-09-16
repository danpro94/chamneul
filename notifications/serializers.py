"""Serializers for the notifications API (SPEC-003, api.md #39-#40).

`actor_user` is stored on the model but is **never serialized**. All five
notification types in Phase 2 are triggered by an admin (advice approve/reject,
application approve/reject, assignment), so exposing the actor would hand a
concern author or advisor an administrator's account id (spec.md §7 결정 1,
CLAUDE.md §8 — response fields must be intentionally chosen). `payload` is
likewise internal: the client resolves a destination from (type, target_url).
"""

from rest_framework import serializers

from .models import Notification, NotificationType


class NotificationListSerializer(serializers.ModelSerializer):
    """#39 row. No `read_at` — the list only needs the unread flag."""

    notification_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = Notification
        fields = (
            "notification_id",
            "type",
            "title",
            "message",
            "target_url",
            "is_read",
            "created_at",
        )


class NotificationDetailSerializer(NotificationListSerializer):
    """#40 — the list fields plus `read_at`."""

    class Meta(NotificationListSerializer.Meta):
        fields = NotificationListSerializer.Meta.fields + ("read_at",)


class NotificationReadResultSerializer(serializers.ModelSerializer):
    """#41 response — the three fields the client needs to update its badge.

    Deliberately narrower than the detail serializer: a read acknowledgement
    does not need to re-send the body (api.md #41 Response 주요 필드).
    """

    notification_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = Notification
        fields = ("notification_id", "is_read", "read_at")


class NotificationQuerySerializer(serializers.Serializer):
    """#39 query parameters.

    Validated rather than best-effort parsed (Owner decision 2026-09-16,
    SPEC-003 리뷰 AR-02; same shape SPEC-002 gave #26/#31/#32 on 2026-09-14).
    Silently ignoring `?is_read=banana` is the worst of the options available:
    the caller asked to narrow the list and got **every** notification back,
    read ones included, with no indication the filter was dropped.
    """

    is_read = serializers.BooleanField(required=False, allow_null=True, default=None)
    type = serializers.ChoiceField(
        choices=NotificationType.choices, required=False, allow_null=True, default=None
    )
