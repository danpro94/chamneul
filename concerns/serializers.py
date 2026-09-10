"""Serializers for concerns API (SPEC-001, api.md #16-#18).

List/create/detail are kept separate (CLAUDE.md §8-§9): the create response is
minimal (concern_id/status/message), the list response excludes large text
fields (decision_context) and internal-only fields (display_alias), and only
the detail response carries the nested approved_advices[].
"""

from rest_framework import serializers

from . import services
from .models import Concern


class ConcernCreateSerializer(serializers.ModelSerializer):
    """POST /api/v1/users/me/concerns (#16) request body.

    `author`/`status`/`deleted_at` are server-controlled and excluded — the
    view sets `author=request.user`; `status` defaults to SUBMITTED on the
    model. `concern_type`'s choices and `concern_type_secondary`'s max size
    (model.md §3.6: ArrayField size=2) are enforced automatically by
    ModelSerializer field generation, so no field is redeclared here.
    """

    class Meta:
        model = Concern
        fields = (
            "concern_summary",
            "concern_type",
            "concern_type_secondary",
            "preferred_advisor_lane",
            "decision_context",
            "display_alias",
            "is_anonymous",
        )


class ConcernCreateResultSerializer(serializers.ModelSerializer):
    """#16 response — concern_id, status, message only (api.md #16)."""

    concern_id = serializers.UUIDField(source="id", read_only=True)
    message = serializers.SerializerMethodField()

    class Meta:
        model = Concern
        fields = ("concern_id", "status", "message")
        read_only_fields = fields

    def get_message(self, obj):
        return "고민이 등록되었습니다."


class ConcernListSerializer(serializers.ModelSerializer):
    """GET /api/v1/users/me/concerns (#17) list item (api.md #17 response
    fields). `has_approved_advice` is a queryset annotation, not a DB column
    (services.list_my_concerns) — declared read-only here for that reason.
    """

    concern_id = serializers.UUIDField(source="id", read_only=True)
    has_approved_advice = serializers.BooleanField(read_only=True)

    class Meta:
        model = Concern
        fields = (
            "concern_id",
            "concern_summary",
            "concern_type",
            "status",
            "has_approved_advice",
            "created_at",
        )
        read_only_fields = fields


class ConcernDetailSerializer(serializers.ModelSerializer):
    """GET /api/v1/users/me/concerns/{concern-id} (#18) — full own-resource
    detail (api.md #18 response fields). `approved_advices` is built by
    services.approved_advices_view_data (CLAUDE.md §6.2: APPROVED-only).
    """

    concern_id = serializers.UUIDField(source="id", read_only=True)
    approved_advices = serializers.SerializerMethodField()

    class Meta:
        model = Concern
        fields = (
            "concern_id",
            "concern_summary",
            "concern_type",
            "concern_type_secondary",
            "preferred_advisor_lane",
            "decision_context",
            "is_anonymous",
            "status",
            "created_at",
            "approved_advices",
        )
        read_only_fields = fields

    def get_approved_advices(self, obj):
        return services.approved_advices_view_data(obj)
