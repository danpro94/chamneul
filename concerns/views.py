"""Views for concerns API (SPEC-001 TASK-001: api.md #16 create + #17 list).

#16 and #17 share one path (POST/GET on /api/v1/users/me/concerns), so they
are one APIView rather than two — the same shape as accounts.UserMeView
(GET+PATCH on one path).
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import StandardPagination

from . import services
from .serializers import (
    ConcernCreateResultSerializer,
    ConcernCreateSerializer,
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
