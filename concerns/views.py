"""Views for concerns API (SPEC-001: api.md #16-#19).

#16/#17 share one path (POST/GET on .../concerns) and #18/#19 share another
(GET/DELETE on .../concerns/{concern-id}) — each pair is one APIView, the
same shape as accounts.UserMeView (GET+PATCH on one path).
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import StandardPagination

from . import services
from .serializers import (
    ConcernCreateResultSerializer,
    ConcernCreateSerializer,
    ConcernDetailSerializer,
    ConcernListSerializer,
)


class ConcernListCreateView(APIView):
    """GET (#17) / POST (#16) — /api/v1/users/me/concerns.

    No active_role gate (spec.md §3, Owner-approved 2026-09-09): a concern is
    self-owned and creating/listing it is role-independent.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get(self, request):
        queryset = services.list_my_concerns(request.user)
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ConcernListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ConcernCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        concern = services.create_concern(request.user, serializer.validated_data)
        return Response(ConcernCreateResultSerializer(concern).data, status=201)


class ConcernDetailView(APIView):
    """GET (#18) / DELETE (#19) — /api/v1/users/me/concerns/{concern-id}.

    Object-level access control (CLAUDE.md §10): both actions look the
    concern up scoped to `author=request.user`, so another user's concern is
    404, never 403 (its existence is not revealed).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, concern_id):
        concern = services.get_own_concern(request.user, concern_id)
        return Response(ConcernDetailSerializer(concern).data)

    def delete(self, request, concern_id):
        concern = services.get_own_concern_including_deleted(request.user, concern_id)
        services.soft_delete_concern(concern)
        return Response(status=204)
