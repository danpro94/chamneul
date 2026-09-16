from django.contrib import admin
from django.utils import timezone

from .models import Assignment, Concern, ConcernStatus


@admin.register(Concern)
class ConcernAdmin(admin.ModelAdmin):
    list_display = ("author", "concern_summary", "status", "deleted_at", "created_at")
    list_filter = ("status", "concern_type", ("deleted_at", admin.EmptyFieldListFilter))
    search_fields = ("concern_summary", "author__email")
    list_select_related = ("author",)
    # status는 readonly다 (Owner decision 2026-09-16, SPEC-004 리뷰 B-04).
    # 자유 편집을 열어두면 ANSWERED->SUBMITTED 같은 역전이까지 함께 열린다
    # (CLAUDE.md §6.6 상태 머신에 그 간선이 없다). Phase 2에 CLOSED 전이
    # 사용자 API가 없다는 결정(SPEC-004 §5 결정 5)은 아래 전용 action이
    # 감당한다 — 한 방향만 여는 것이 자유 편집보다 안전하다.
    readonly_fields = ("id", "status", "deleted_at", "created_at", "updated_at")
    actions = ("close_selected", "soft_delete_selected", "restore_selected")

    def get_queryset(self, request):
        # Admin은 감사 목적상 soft-deleted 포함 전체를 본다 (model.md §1.4).
        return Concern.objects.with_deleted().select_related("author")

    @admin.action(description="선택한 고민 종료 (ANSWERED -> CLOSED)")
    def close_selected(self, request, queryset):
        """§6.6이 허용하는 유일한 방향(ANSWERED -> CLOSED)만 수행한다.
        다른 상태의 고민은 건드리지 않고 건수만 알린다."""
        updated = queryset.filter(status=ConcernStatus.ANSWERED).update(
            status=ConcernStatus.CLOSED
        )
        skipped = queryset.count() - updated
        msg = f"{updated}건 종료"
        if skipped:
            msg += f" / {skipped}건 건너뜀 (ANSWERED 상태가 아님)"
        self.message_user(request, msg)

    @admin.action(description="선택한 고민 soft delete (deleted_at 기록)")
    def soft_delete_selected(self, request, queryset):
        updated = queryset.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())
        self.message_user(request, f"{updated}건 soft delete 처리")

    @admin.action(description="선택한 고민 복구 (deleted_at 해제)")
    def restore_selected(self, request, queryset):
        updated = queryset.exclude(deleted_at__isnull=True).update(deleted_at=None)
        self.message_user(request, f"{updated}건 복구")


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    """View-only (Owner decision 2026-09-16, SPEC-004 리뷰 B-01).

    배정은 세 가지가 함께 일어나야 성립한다 — Assignment 행, concern의
    SUBMITTED->ASSIGNED 전이, 조언가에게 가는 ASSIGNMENT_CREATED 알림
    (concerns.services.assign_advisor). 이 화면에서 행만 추가하면 나머지 둘이
    빠진 반쪽 상태가 되고, 행을 지우면 "비활성 보존"이어야 할 감사 기록이
    물리적으로 사라진다. 생성·해제는 #24/#25로만 한다.
    """

    list_display = ("concern", "advisor", "is_active", "priority", "assigned_at")
    list_filter = ("is_active", "priority")
    search_fields = ("advisor__email", "concern__concern_summary")
    list_select_related = ("concern", "advisor", "assigned_by")
    readonly_fields = (
        "id", "concern", "advisor", "assigned_by", "triage_decision",
        "match_rationale", "priority", "is_active", "assigned_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
