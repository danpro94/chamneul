"""Serializers for the advice API (SPEC-002, api.md #26-#38).

Request and response shapes are separate classes throughout (CLAUDE.md §8-§9):
the same advice is shown with different fields to its author, the concern
owner and an admin, so no single "advice serializer" would be honest.
"""

from rest_framework import serializers

from .models import Advice, AdviceStatus


class AdviceCreateSerializer(serializers.ModelSerializer):
    """POST /api/v1/concerns/{concern-id}/advices (#28) request body.

    `concern`/`advisor`/`status`/`version` are server-controlled and excluded.
    `directional_guidance`'s 1500-char limit comes from the model's validator,
    which ModelSerializer copies onto the generated field — so no redeclaration.
    """

    submit = serializers.BooleanField(default=True)

    class Meta:
        model = Advice
        fields = (
            "directional_guidance",
            "reflective_questions",
            "considerations",
            "out_of_scope_flag",
            "submit",
        )


class AdviceCreateResultSerializer(serializers.ModelSerializer):
    """#28 response — api.md #28 field set."""

    advice_id = serializers.UUIDField(source="id", read_only=True)
    concern_id = serializers.UUIDField(read_only=True)
    advisor_user_id = serializers.UUIDField(source="advisor_id", read_only=True)

    class Meta:
        model = Advice
        fields = (
            "advice_id",
            "concern_id",
            "advisor_user_id",
            "status",
            "version",
            "created_at",
        )
        read_only_fields = fields


class AdviceWrittenListSerializer(serializers.ModelSerializer):
    """GET /api/v1/users/me/advices-written (#31) list item.

    Advisor-facing, so it carries `is_submitted` (draft vs submitted, D-3) and
    `version`, but no body text — the list must stay light (CLAUDE.md §8).
    """

    advice_id = serializers.UUIDField(source="id", read_only=True)
    concern_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Advice
        fields = (
            "advice_id",
            "concern_id",
            "status",
            "version",
            "is_submitted",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AdviceWrittenQuerySerializer(serializers.Serializer):
    """#31 query params. Validating them here turns a malformed status or
    date into 400 instead of a silently empty page."""

    concern_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(choices=AdviceStatus.choices, required=False)
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)
