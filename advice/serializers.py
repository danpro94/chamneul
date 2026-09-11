"""Serializers for the advice API (SPEC-002, api.md #26-#38).

Request and response shapes are separate classes throughout (CLAUDE.md §8-§9):
the same advice is shown with different fields to its author, the concern
owner and an admin, so no single "advice serializer" would be honest.
"""

from rest_framework import serializers

from concerns.services import display_names_by_advisor

from .models import Advice, AdviceStatus, Feedback, FeedbackStatus


class _AdvisorDisplayNameMixin:
    """`advisor_display_name` (api.md #26/#27): resolved via the advisor's
    most recent APPROVED advisor application, falling back to their account
    nickname — same rule as concerns.services.approved_advices_view_data.
    A single-object lookup here (unlike the bulk one a list view needs).
    """

    def get_advisor_display_name(self, obj):
        names = display_names_by_advisor([obj.advisor_id])
        return names.get(obj.advisor_id, obj.advisor.nickname)


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


class AdviceDetailSerializer(_AdvisorDisplayNameMixin, serializers.ModelSerializer):
    """GET /api/v1/advices/{advice-id} (#27) — the concern-owner shape.

    No `reject_reason`: the concern owner only ever reaches this serializer
    for an APPROVED advice (services.get_visible_advice), where the field
    would be empty anyway, but CLAUDE.md §8 asks for intentional field
    selection, not "empty so it's harmless".
    """

    advice_id = serializers.UUIDField(source="id", read_only=True)
    concern_id = serializers.UUIDField(read_only=True)
    advisor_display_name = serializers.SerializerMethodField()

    class Meta:
        model = Advice
        fields = (
            "advice_id",
            "concern_id",
            "advisor_display_name",
            "directional_guidance",
            "reflective_questions",
            "considerations",
            "out_of_scope_flag",
            "status",
            "version",
            "is_submitted",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AdviceDetailWithReasonSerializer(AdviceDetailSerializer):
    """#27 — the author/admin shape: everything above plus `reject_reason`
    (api.md #27: "작성자/Admin에게만, D-3")."""

    class Meta(AdviceDetailSerializer.Meta):
        fields = AdviceDetailSerializer.Meta.fields + ("reject_reason",)
        read_only_fields = fields


class AdviceUpdateSerializer(serializers.ModelSerializer):
    """PATCH /api/v1/advices/{advice-id} (#29) request body — every field is
    optional (partial update). `submit` maps onto the model's `is_submitted`.
    """

    submit = serializers.BooleanField(source="is_submitted", required=False)

    class Meta:
        model = Advice
        fields = (
            "directional_guidance",
            "reflective_questions",
            "considerations",
            "out_of_scope_flag",
            "submit",
        )
        extra_kwargs = {
            "directional_guidance": {"required": False},
            "reflective_questions": {"required": False},
            "considerations": {"required": False},
            "out_of_scope_flag": {"required": False},
        }


class AdviceUpdateResultSerializer(serializers.ModelSerializer):
    """#29 response — api.md #29 field set."""

    advice_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = Advice
        fields = ("advice_id", "status", "version", "updated_at")
        read_only_fields = fields


class AdviceWrittenQuerySerializer(serializers.Serializer):
    """#31 query params. Validating them here turns a malformed status or
    date into 400 instead of a silently empty page."""

    concern_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(choices=AdviceStatus.choices, required=False)
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)


class AdminAdviceListSerializer(serializers.ModelSerializer):
    """GET /api/v1/admin/advices (#32) list item (api.md #32 response
    fields). No advisor_display_name here — the review queue works off the
    raw advisor_user_id; api.md doesn't ask for the display name at this
    level (contrast #26/#27, which are user-facing).
    """

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
            "updated_at",
        )
        read_only_fields = fields


class AdviceReviewSerializer(serializers.Serializer):
    """PATCH /api/v1/admin/advices/{advice-id}/review (#33) request.

    `reason`-required-on-reject is a semantic check (422) owned by
    services.review_advice, not this shape validator (400) — same split as
    advisors.serializers.AdvisorApplicationReviewSerializer.
    """

    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    expected_version = serializers.IntegerField(min_value=1)


class ReceivedAdviceListSerializer(serializers.ModelSerializer):
    """GET /api/v1/users/me/advices (#26) list item (api.md #26 fields).

    `advisor_display_name` is resolved in bulk by the view and handed in via
    context — unlike the single-object #27 path, a per-row lookup here would
    be N+1 (CLAUDE.md §8). `is_feedback_submitted` is a queryset annotation.
    """

    advice_id = serializers.UUIDField(source="id", read_only=True)
    concern_id = serializers.UUIDField(read_only=True)
    concern_summary = serializers.CharField(
        source="concern.concern_summary", read_only=True
    )
    advisor_display_name = serializers.SerializerMethodField()
    is_feedback_submitted = serializers.BooleanField(read_only=True)

    class Meta:
        model = Advice
        fields = (
            "advice_id",
            "concern_id",
            "concern_summary",
            "advisor_display_name",
            "created_at",
            "is_feedback_submitted",
        )
        read_only_fields = fields

    def get_advisor_display_name(self, obj):
        return self.context["display_names"].get(obj.advisor_id, obj.advisor.nickname)


class ReceivedAdviceQuerySerializer(serializers.Serializer):
    """#26 query params — validated so a malformed date is 400, not an
    empty page."""

    keyword = serializers.CharField(required=False, allow_blank=True)
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)


class FeedbackCreateSerializer(serializers.ModelSerializer):
    """POST /api/v1/advices/{advice-id}/feedbacks (#34) request body.

    `score`'s 1..5 range comes from the model's validators, which
    ModelSerializer copies onto the field — the same mechanism that caps
    directional_guidance at 1500 chars.
    """

    class Meta:
        model = Feedback
        fields = ("score", "content")


class FeedbackCreateResultSerializer(serializers.ModelSerializer):
    """#34 response — api.md #34 field set."""

    feedback_id = serializers.UUIDField(source="id", read_only=True)
    advice_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Feedback
        fields = ("feedback_id", "advice_id", "status", "created_at")
        read_only_fields = fields


class MyFeedbackListSerializer(serializers.ModelSerializer):
    """GET /api/v1/users/me/feedbacks (#35) list item. No admin-only fields
    (`memo`, `reviewed_by`) — those belong to #37 only."""

    feedback_id = serializers.UUIDField(source="id", read_only=True)
    advice_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Feedback
        fields = (
            "feedback_id",
            "advice_id",
            "score",
            "content",
            "status",
            "created_at",
        )
        read_only_fields = fields


class AdminFeedbackQuerySerializer(serializers.Serializer):
    """#36 query params. `score_min`/`score_max` are bounded to the model's
    1..5 range, so a nonsense filter is 400 rather than an empty page."""

    status = serializers.ChoiceField(choices=FeedbackStatus.choices, required=False)
    score_min = serializers.IntegerField(min_value=1, max_value=5, required=False)
    score_max = serializers.IntegerField(min_value=1, max_value=5, required=False)


class AdminFeedbackListSerializer(serializers.ModelSerializer):
    """GET /api/v1/admin/feedbacks (#36) list item (api.md #36 fields).

    Carries both parties' ids — `author_user_id` (who wrote the feedback) and
    `advisor_user_id` (whose advice it is about) — but no body text; the
    content belongs to the #37 detail (CLAUDE.md §8).
    """

    feedback_id = serializers.UUIDField(source="id", read_only=True)
    advice_id = serializers.UUIDField(read_only=True)
    advisor_user_id = serializers.UUIDField(source="advice.advisor_id", read_only=True)
    author_user_id = serializers.UUIDField(source="author_id", read_only=True)

    class Meta:
        model = Feedback
        fields = (
            "feedback_id",
            "advice_id",
            "advisor_user_id",
            "author_user_id",
            "score",
            "status",
            "created_at",
        )
        read_only_fields = fields


class AdminFeedbackDetailSerializer(serializers.ModelSerializer):
    """GET /api/v1/admin/feedbacks/{feedback-id} (#37).

    The only place `memo` and `author_nickname` are exposed — both are
    admin-only (model.md §3.10). The feedback's author sees neither on #35.
    """

    feedback_id = serializers.UUIDField(source="id", read_only=True)
    advice_id = serializers.UUIDField(read_only=True)
    advisor_user_id = serializers.UUIDField(source="advice.advisor_id", read_only=True)
    author_user_id = serializers.UUIDField(source="author_id", read_only=True)
    author_nickname = serializers.CharField(source="author.nickname", read_only=True)
    reviewed_by = serializers.UUIDField(source="reviewed_by_id", read_only=True)

    class Meta:
        model = Feedback
        fields = (
            "feedback_id",
            "advice_id",
            "advisor_user_id",
            "author_user_id",
            "author_nickname",
            "score",
            "content",
            "status",
            "reviewed_at",
            "reviewed_by",
            "memo",
            "created_at",
        )
        read_only_fields = fields


class AdminFeedbackTransitionSerializer(serializers.Serializer):
    """PATCH /api/v1/admin/feedbacks/{feedback-id} (#38) request.

    Whether the requested transition is legal is a state question (409) owned
    by services.transition_feedback — this only validates the shape (400).
    """

    status = serializers.ChoiceField(choices=FeedbackStatus.choices)
    memo = serializers.CharField(required=False, allow_blank=True)


class AdminFeedbackTransitionResultSerializer(serializers.ModelSerializer):
    """#38 response — api.md #38 field set."""

    feedback_id = serializers.UUIDField(source="id", read_only=True)
    reviewed_by = serializers.UUIDField(source="reviewed_by_id", read_only=True)

    class Meta:
        model = Feedback
        fields = ("feedback_id", "status", "reviewed_at", "reviewed_by")
        read_only_fields = fields
