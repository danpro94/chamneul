"""Views for concerns API (SPEC-001: api.md #16-#21).

#16/#17 share one path (POST/GET on .../concerns) and #18/#19 share another
(GET/DELETE on .../concerns/{concern-id}) — each pair is one APIView, the
same shape as accounts.UserMeView (GET+PATCH on one path). #20/#21 are the
advisor-side counterpart under .../assigned-concerns.
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import StandardPagination
from common.permissions import IsActiveAdvisor, IsAdmin

from . import services
from .serializers import (
    AdminConcernListSerializer,
    AssignedConcernListSerializer,
    AssignmentCreateResultSerializer,
    AssignmentCreateSerializer,
    ConcernCreateResultSerializer,
    ConcernCreateSerializer,
    ConcernDetailSerializer,
    ConcernListSerializer,
)

# api.md §1.6 query flags are strings; treat the usual truthy spellings as true.
_TRUE_VALUES = {"true", "1", "yes", "on"}


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


class AssignedConcernListView(APIView):
    """GET (#20) — /api/v1/users/me/assigned-concerns.

    Requires active_role=ADVISOR, not just holding the role (CLAUDE.md §2
    Roles — see IsActiveAdvisor). `status` filters by the *concern's* status
    (Owner decision 2026-09-10, STATUS.md §5): Assignment has no status enum,
    and its is_active flag is already the list's precondition.
    """

    permission_classes = [IsAuthenticated, IsActiveAdvisor]
    pagination_class = StandardPagination

    def get(self, request):
        queryset = services.list_assigned_concerns(request.user)
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(concern__status=status_filter)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AssignedConcernListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AssignedConcernDetailView(APIView):
    """GET (#21) — /api/v1/users/me/assigned-concerns/{concern-id}.

    404 if the concern doesn't exist, 403 if it exists but isn't assigned to
    this advisor (api.md #21 — unlike #18, existence is not hidden here).
    """

    permission_classes = [IsAuthenticated, IsActiveAdvisor]

    def get(self, request, concern_id):
        concern, assignment = services.get_assigned_concern(request.user, concern_id)
        data = services.assigned_concern_detail_view_data(concern, assignment, request.user)
        return Response(data)


class AdminConcernListView(APIView):
    """GET (#22) — /api/v1/admin/concerns. Every user's concerns, ADMIN only."""

    permission_classes = [IsAdmin]
    pagination_class = StandardPagination

    def get(self, request):
        include_deleted = request.query_params.get("include_deleted", "").lower() in _TRUE_VALUES
        queryset = services.list_concerns_for_admin(include_deleted=include_deleted)

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        keyword = request.query_params.get("keyword")
        if keyword:
            queryset = queryset.filter(concern_summary__icontains=keyword)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AdminConcernListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminConcernDetailView(APIView):
    """GET (#23) — /api/v1/admin/concerns/{concern-id}.

    Shows every assignment and advice regardless of state, and reaches
    soft-deleted concerns (admin/audit path, CLAUDE.md §6.6).
    """

    permission_classes = [IsAdmin]

    def get(self, request, concern_id):
        concern = services.get_concern_for_admin(concern_id)
        return Response(services.admin_concern_detail_view_data(concern))


class AdminAssignmentCreateView(APIView):
    """POST (#24) — /api/v1/admin/concerns/{concern-id}/assignments.

    1 concern <-> N advisors (api.md Q9). The state transition and the
    advisor notification are side effects of services.assign_advisor, which
    runs them in one transaction.
    """

    permission_classes = [IsAdmin]

    def post(self, request, concern_id):
        serializer = AssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment, concern = services.assign_advisor(
            concern_id, request.user, serializer.validated_data
        )
        result = AssignmentCreateResultSerializer(
            assignment, context={"concern_status": concern.status}
        )
        return Response(result.data, status=201)


class AdminAssignmentDetailView(APIView):
    """DELETE (#25) — .../concerns/{concern-id}/assignments/{assignment-id}."""

    permission_classes = [IsAdmin]

    def delete(self, request, concern_id, assignment_id):
        services.unassign_advisor(concern_id, assignment_id)
        return Response(status=204)
