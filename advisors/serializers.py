from rest_framework import serializers

from .models import AdvisorApplication


class AdvisorApplicationCreateSerializer(serializers.ModelSerializer):
    """POST /advisor-applications (#11) request.

    Excludes advisor_type and real_name entirely (CLAUDE.md §6.1 — not in the
    public form). intended_lane IS accepted as applicant-stated intent, but is
    never echoed to the public (#12 omits it); only admin detail (#14) shows it.
    """

    # Declared explicitly to drop DRF's auto UniqueValidator (from the partial
    # UniqueConstraint on display_name), which would otherwise return 400 before
    # the service can decide. Conflicts are the service's job -> 409 (api.md #11).
    display_name = serializers.CharField(max_length=20, min_length=2)

    class Meta:
        model = AdvisorApplication
        fields = (
            "display_name",
            "domain_category",
            "experience_band",
            "current_status",
            "intended_lane",
            "career_narrative",
            "advisable_concern_types",
            "sample_advice_response",
        )

    def validate_advisable_concern_types(self, value):
        if not value:
            raise serializers.ValidationError("최소 1개 이상 선택해야 합니다.")
        return value


class AdvisorApplicationCreateResultSerializer(serializers.ModelSerializer):
    """#11 response — minimal: application_id, status, submitted_at."""

    application_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = AdvisorApplication
        fields = ("application_id", "status", "submitted_at")
        read_only_fields = fields


class AdvisorApplicationMeSerializer(serializers.ModelSerializer):
    """GET /advisor-applications/me (#12). intended_lane is deliberately absent
    (CLAUDE.md §6.1 — never returned to the applicant or any public view).
    """

    application_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = AdvisorApplication
        fields = (
            "application_id",
            "display_name",
            "status",
            "submitted_at",
            "reviewed_at",
            "reject_reason",
        )
        read_only_fields = fields


class AdvisorApplicationAdminListSerializer(serializers.ModelSerializer):
    """GET /admin/advisor-applications (#13). List view: no intended_lane, no
    heavy text fields."""

    application_id = serializers.UUIDField(source="id", read_only=True)
    applicant_user_id = serializers.UUIDField(source="applicant_id", read_only=True)

    class Meta:
        model = AdvisorApplication
        fields = (
            "application_id",
            "applicant_user_id",
            "display_name",
            "status",
            "submitted_at",
        )
        read_only_fields = fields


class AdvisorApplicationAdminDetailSerializer(serializers.ModelSerializer):
    """GET /admin/advisor-applications/{id} (#14). The only view that exposes
    intended_lane (admin review tooling only — CLAUDE.md §6.1)."""

    application_id = serializers.UUIDField(source="id", read_only=True)
    applicant_user_id = serializers.UUIDField(source="applicant_id", read_only=True)
    reviewed_by = serializers.UUIDField(source="reviewed_by_id", read_only=True)

    class Meta:
        model = AdvisorApplication
        fields = (
            "application_id",
            "applicant_user_id",
            "display_name",
            "domain_category",
            "experience_band",
            "current_status",
            "intended_lane",
            "career_narrative",
            "advisable_concern_types",
            "sample_advice_response",
            "status",
            "submitted_at",
            "reviewed_at",
            "reviewed_by",
            "reject_reason",
        )
        read_only_fields = fields


class AdvisorApplicationReviewSerializer(serializers.Serializer):
    """PATCH /admin/advisor-applications/{id} (#15) request. The
    reject_reason-required rule is a semantic check (422) enforced in the
    service, not here (this only validates request shape -> 400)."""

    status = serializers.ChoiceField(choices=["REVIEWING", "APPROVED", "REJECTED"])
    reject_reason = serializers.CharField(required=False, allow_blank=True, default="")
