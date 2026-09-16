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
from .serializers import (
    NotificationDetailSerializer,
    NotificationListSerializer,
    NotificationQuerySerializer,
    NotificationReadResultSerializer,
)


class NotificationListView(APIView):
    """GET (#39) — /api/v1/notifications."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get(self, request):
        query = NotificationQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)  # 400 on an unusable filter
        queryset = services.list_my_notifications(
            request.user,
            is_read=query.validated_data["is_read"],
            notification_type=query.validated_data["type"],
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


class NotificationReadView(APIView):
    """PATCH (#41) — /api/v1/notifications/{notification-id}/read.

    No request body: the resource is the read state and PATCH sets it. Re-reading
    is a no-op that still answers 200 (services.mark_read).
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, notification_id):
        notification = services.mark_read(request.user, notification_id)
        return Response(NotificationReadResultSerializer(notification).data)
