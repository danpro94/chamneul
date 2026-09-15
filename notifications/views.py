"""Views for the notifications API (SPEC-003: api.md #39-#40).

No object-level permission class is needed: the service layer scopes every
queryset to `recipient=request.user`, which is the access control itself
(services.py docstring). IsAuthenticated is therefore the only gate.
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import StandardPagination

from . import services
from .serializers import NotificationDetailSerializer, NotificationListSerializer

# api.md §1.6 query flags are strings (mirrors concerns/views.py). `is_read` is
# tri-state — absent means "no filter" — so it needs both spellings.
_TRUE_VALUES = {"true", "1", "yes", "on"}
_FALSE_VALUES = {"false", "0", "no", "off"}


def _parse_is_read(raw):
    """None when absent or unrecognised. #39's status set has no 400, so an
    unparseable value is treated as "no filter" rather than an error."""
    if raw is None:
        return None
    lowered = raw.strip().lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    return None


class NotificationListView(APIView):
    """GET (#39) — /api/v1/notifications."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get(self, request):
        queryset = services.list_my_notifications(
            request.user,
            is_read=_parse_is_read(request.query_params.get("is_read")),
            notification_type=request.query_params.get("type"),
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = NotificationListSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)
        # Added onto the shared {items, page_info} envelope rather than into
        # StandardPagination — ten other list endpoints share that class and
        # none of them has an unread count.
        response.data["unread_count"] = services.unread_count(request.user)
        return response


class NotificationDetailView(APIView):
    """GET (#40) — /api/v1/notifications/{notification-id}."""

    permission_classes = [IsAuthenticated]

    def get(self, request, notification_id):
        notification = services.get_my_notification(request.user, notification_id)
        return Response(NotificationDetailSerializer(notification).data)
