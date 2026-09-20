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
    # 사실상 view-only다 (Owner decision 2026-09-16, SPEC-004 리뷰 B-02).
    # status/reviewed_*를 막은 것만으로는 부족했다 — 본문 4필드가 열려 있어
    # 이 화면에서 조언을 고치면 AdviceHistory 스냅샷도 version 증가도 없이
    # 내용만 바뀌었다. "버전마다 직전 본문을 보존한다"(CLAUDE.md §6.7 / ADR-007)
    # 는 불변식이 깨지고, APPROVED 조언의 본문까지 수정 가능했다.
    # 수정은 #29로만 한다.
    readonly_fields = (
        "id",
        "concern",
        "advisor",
        "directional_guidance",
        "reflective_questions",
        "considerations",
        "out_of_scope_flag",
        "is_submitted",
        "status",
        "reject_reason",
        "reviewed_at",
        "reviewed_by",
        "version",
        "created_at",
        "updated_at",
    )


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
    """상태는 readonly (Owner decision 2026-09-16, SPEC-004 리뷰 B-03).

    SUBMITTED -> REVIEWED -> ARCHIVED는 단방향이고 한 칸씩이다(CLAUDE.md §6.3).
    이 화면에서 `status`를 자유 편집하면 역전이와 건너뛰기가 모두 가능했고,
    `reviewed_by`/`reviewed_at`도 찍히지 않았다. 전이는 #38로만 한다.
    """

    list_display = ("advice", "author", "score", "status", "created_at")
    list_filter = ("status", "score")
    search_fields = ("author__email",)
    list_select_related = ("advice", "author")
    # `memo`만 편집 가능하게 남긴다 — 관리자 자신의 작업 메모라 도메인
    # 부수효과가 없고, 이 화면의 실질적 용도이기도 하다(model.md §3.10).
    readonly_fields = (
        "id", "advice", "author", "score", "content",
        "status", "reviewed_by", "reviewed_at", "created_at",
    )
