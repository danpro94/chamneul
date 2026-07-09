from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdmin

from . import services
from .models import AdvisorApplication
from .serializers import (
    AdvisorApplicationAdminDetailSerializer,
    AdvisorApplicationAdminListSerializer,
    AdvisorApplicationCreateResultSerializer,
    AdvisorApplicationCreateSerializer,
    AdvisorApplicationMeSerializer,
    AdvisorApplicationReviewSerializer,
)


class AdvisorApplicationView(APIView):
    """POST /api/v1/advisor-applications (#11) — submit an application."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AdvisorApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = services.create_application(request.user, serializer.validated_data)
        return Response(
            AdvisorApplicationCreateResultSerializer(application).data, status=201
        )


class AdvisorApplicationMeView(APIView):
    """GET /api/v1/advisor-applications/me (#12) — my latest application, or 404."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        application = (
            AdvisorApplication.objects.filter(applicant=request.user)
            .order_by("-submitted_at")
            .first()
        )
        if application is None:
            return Response({"detail": "신청 이력이 없습니다."}, status=404)
        return Response(AdvisorApplicationMeSerializer(application).data)


class AdminAdvisorApplicationListView(ListAPIView):
    """GET /api/v1/admin/advisor-applications (#13) — paginated list, ?status."""

    permission_classes = [IsAdmin]
    serializer_class = AdvisorApplicationAdminListSerializer

    def get_queryset(self):
        qs = AdvisorApplication.objects.select_related("applicant").order_by("-submitted_at")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class AdminAdvisorApplicationDetailView(APIView):
    """GET (#14) / PATCH review (#15) /api/v1/admin/advisor-applications/{id}."""

    permission_classes = [IsAdmin]

    def get(self, request, application_id):
        application = get_object_or_404(
            AdvisorApplication.objects.select_related("applicant", "reviewed_by"),
            pk=application_id,
        )
        return Response(AdvisorApplicationAdminDetailSerializer(application).data)

    def patch(self, request, application_id):
        application = get_object_or_404(AdvisorApplication, pk=application_id)
        serializer = AdvisorApplicationReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.review_application(
            application,
            actor=request.user,
            target_status=serializer.validated_data["status"],
            reject_reason=serializer.validated_data.get("reject_reason", ""),
        )
        return Response(
            {
                "application_id": str(application.id),
                "status": application.status,
                "reviewed_at": application.reviewed_at,
                "reviewed_by": str(application.reviewed_by_id),
            }
        )
