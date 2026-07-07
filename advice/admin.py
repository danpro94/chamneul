from django.contrib import admin

from .models import Advice, AdviceHistory, Feedback


@admin.register(Advice)
class AdviceAdmin(admin.ModelAdmin):
    # Review(approve/reject) action은 M4 서비스 레이어와 함께 — 부수효과
    # (concern 상태 전이 + Notification)를 모델 단계에서 흉내내지 않는다.
    list_display = ("concern", "advisor", "status", "version", "created_at")
    list_filter = ("status",)
    search_fields = ("advisor__email", "concern__concern_summary")
    list_select_related = ("concern", "advisor")
    # version은 감사 카운터 — 수동 편집 금지 (CLAUDE.md §6.7)
    readonly_fields = ("id", "version", "created_at", "updated_at")


@admin.register(AdviceHistory)
class AdviceHistoryAdmin(admin.ModelAdmin):
    """View-only: 스냅샷은 서비스 코드가 쓰는 감사 기록이다 (model.md §3.9)."""

    list_display = ("advice", "version", "edited_by", "edited_at")
    search_fields = ("advice__advisor__email",)
    list_select_related = ("advice", "edited_by")
    readonly_fields = (
        "id",
        "advice",
        "version",
        "directional_guidance",
        "reflective_questions",
        "considerations",
        "out_of_scope_flag",
        "edited_by",
        "edited_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("advice", "author", "score", "status", "created_at")
    list_filter = ("status", "score")
    search_fields = ("author__email",)
    list_select_related = ("advice", "author")
    readonly_fields = ("id", "created_at")
