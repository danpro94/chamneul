"""Views for the advice API (SPEC-002: api.md #26-#38).

TASK-001 covers #28 (author an advice) and #31 (the advisor's own list).
Both require the caller to be *switched into* the ADVISOR role, not merely to
hold it (api.md §2 Roles — "활성 역할을 ADVISOR로 전환하면 … 조언 작성 가능").
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import StandardPagination
from common.permissions import IsActiveAdvisor, IsAdmin
from concerns.services import display_names_by_advisor

from . import services
from .serializers import (
    AdminAdviceListSerializer,
    AdviceCreateResultSerializer,
    AdviceCreateSerializer,
    AdviceDetailSerializer,
    AdviceDetailWithReasonSerializer,
    AdviceReviewSerializer,
    AdviceUpdateResultSerializer,
    AdviceUpdateSerializer,
    AdviceWrittenListSerializer,
    AdviceWrittenQuerySerializer,
    FeedbackCreateResultSerializer,
    FeedbackCreateSerializer,
    MyFeedbackListSerializer,
    ReceivedAdviceListSerializer,
    ReceivedAdviceQuerySerializer,
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
    """GET (#27) / PATCH (#29) / DELETE (#30) — /api/v1/advices/{advice-id}.

    GET is open to the three audiences resolved by get_visible_advice()
    (spec.md §7-4, CLAUDE.md §6.2). PATCH/DELETE additionally require
    active_role=ADVISOR (api.md #29/#30's "Advisor" permission label — the
    same gate #28/#31 use), so the permission classes differ by method.
    """

    def get_permissions(self):
        if self.request.method in ("PATCH", "DELETE"):
            return [IsAuthenticated(), IsActiveAdvisor()]
        return [IsAuthenticated()]

    def get(self, request, advice_id):
        advice, viewer_role = services.get_visible_advice(advice_id, request.user)
        serializer_class = (
            AdviceDetailWithReasonSerializer
            if viewer_role in {services.VIEWER_AUTHOR, services.VIEWER_ADMIN}
            else AdviceDetailSerializer
        )
        return Response(serializer_class(advice).data)

    def patch(self, request, advice_id):
        serializer = AdviceUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        advice = services.update_advice(
            advice_id, request.user, serializer.validated_data
        )
        return Response(AdviceUpdateResultSerializer(advice).data)

    def delete(self, request, advice_id):
        services.delete_advice(advice_id, request.user)
        return Response(status=204)


class AdminAdviceListView(APIView):
    """GET (#32) — /api/v1/admin/advices. Drafts never appear here (spec.md
    §7-1, Owner decision 2026-09-11) regardless of the `status` filter."""

    permission_classes = [IsAdmin]
    pagination_class = StandardPagination

    def get(self, request):
        queryset = services.list_advices_for_admin_review(
            request.query_params.get("status")
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AdminAdviceListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminAdviceReviewView(APIView):
    """PATCH (#33) — /api/v1/admin/advices/{advice-id}/review.

    Approval/rejection plus their side effects (concern transition,
    notification) are one atomic unit in services.review_advice.
    """

    permission_classes = [IsAdmin]

    def patch(self, request, advice_id):
        serializer = AdviceReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        advice, concern = services.review_advice(
            advice_id,
            request.user,
            decision=data["decision"],
            reason=data["reason"],
            expected_version=data["expected_version"],
        )
        return Response(
            {
                "advice_id": str(advice.id),
                "status": advice.status,
                "review": {
                    "decision": data["decision"],
                    "reviewed_by": str(advice.reviewed_by_id),
                    "reviewed_at": advice.reviewed_at,
                    "reason": advice.reject_reason,
                },
                "concern_id": str(concern.id),
                "concern_status": concern.status,
                "version": advice.version,
            }
        )


class ReceivedAdviceListView(APIView):
    """GET (#26) — /api/v1/users/me/advices.

    The concern owner's inbox: APPROVED advices on their own concerns only
    (CLAUDE.md §6.2). No active_role gate — this is the plain User side,
    same as SPEC-001's #16~#19.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get(self, request):
        query = ReceivedAdviceQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        filters = query.validated_data

        queryset = services.list_received_advices(request.user)
        if filters.get("keyword"):
            queryset = queryset.filter(
                concern__concern_summary__icontains=filters["keyword"]
            )
        if "from_date" in filters:
            queryset = queryset.filter(created_at__date__gte=filters["from_date"])
        if "to_date" in filters:
            queryset = queryset.filter(created_at__date__lte=filters["to_date"])

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        # One bulk lookup for the whole page instead of one per row (§8).
        display_names = display_names_by_advisor([advice.advisor_id for advice in page])
        serializer = ReceivedAdviceListSerializer(
            page, many=True, context={"display_names": display_names}
        )
        return paginator.get_paginated_response(serializer.data)


class FeedbackCreateView(APIView):
    """POST (#34) — /api/v1/advices/{advice-id}/feedbacks. One per advice,
    by the concern's owner, on an APPROVED advice only."""

    permission_classes = [IsAuthenticated]

    def post(self, request, advice_id):
        serializer = FeedbackCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        feedback = services.create_feedback(
            advice_id, request.user, serializer.validated_data
        )
        return Response(FeedbackCreateResultSerializer(feedback).data, status=201)


class MyFeedbackListView(APIView):
    """GET (#35) — /api/v1/users/me/feedbacks."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get(self, request):
        queryset = services.list_feedbacks_written_by(request.user)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = MyFeedbackListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
