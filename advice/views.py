"""Views for the advice API (SPEC-002: api.md #26-#38).

TASK-001 covers #28 (author an advice) and #31 (the advisor's own list).
Both require the caller to be *switched into* the ADVISOR role, not merely to
hold it (api.md §2 Roles — "활성 역할을 ADVISOR로 전환하면 … 조언 작성 가능").
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import StandardPagination
from common.permissions import IsActiveAdvisor

from . import services
from .serializers import (
    AdviceCreateResultSerializer,
    AdviceCreateSerializer,
    AdviceDetailSerializer,
    AdviceDetailWithReasonSerializer,
    AdviceWrittenListSerializer,
    AdviceWrittenQuerySerializer,
)


class AdviceCreateView(APIView):
    """POST (#28) — /api/v1/concerns/{concern-id}/advices."""

    permission_classes = [IsAuthenticated, IsActiveAdvisor]

    def post(self, request, concern_id):
        serializer = AdviceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        advice = services.create_advice(
            concern_id, request.user, serializer.validated_data
        )
        return Response(AdviceCreateResultSerializer(advice).data, status=201)


class AdvicesWrittenView(APIView):
    """GET (#31) — /api/v1/users/me/advices-written. Every status, including
    drafts and DELETED: this is the advisor's own record of their work."""

    permission_classes = [IsAuthenticated, IsActiveAdvisor]
    pagination_class = StandardPagination

    def get(self, request):
        query = AdviceWrittenQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        filters = query.validated_data

        queryset = services.list_advices_written_by(request.user)
        if "concern_id" in filters:
            queryset = queryset.filter(concern_id=filters["concern_id"])
        if "status" in filters:
            queryset = queryset.filter(status=filters["status"])
        if "from_date" in filters:
            queryset = queryset.filter(created_at__date__gte=filters["from_date"])
        if "to_date" in filters:
            queryset = queryset.filter(created_at__date__lte=filters["to_date"])

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AdviceWrittenListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdviceDetailView(APIView):
    """GET (#27) — /api/v1/advices/{advice-id}.

    Three-audience visibility (spec.md §7-4, CLAUDE.md §6.2): the author and
    admin see every status and the reject reason; the concern owner sees only
    an APPROVED advice and never the reject reason; anyone else gets 403.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, advice_id):
        advice, viewer_role = services.get_visible_advice(advice_id, request.user)
        serializer_class = (
            AdviceDetailWithReasonSerializer
            if viewer_role in {services.VIEWER_AUTHOR, services.VIEWER_ADMIN}
            else AdviceDetailSerializer
        )
        return Response(serializer_class(advice).data)
