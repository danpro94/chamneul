from django.contrib import admin
from django.utils import timezone

from .models import Assignment, Concern


@admin.register(Concern)
class ConcernAdmin(admin.ModelAdmin):
    list_display = ("author", "concern_summary", "status", "deleted_at", "created_at")
    list_filter = ("status", "concern_type", ("deleted_at", admin.EmptyFieldListFilter))
    search_fields = ("concern_summary", "author__email")
    list_select_related = ("author",)
    readonly_fields = ("id", "deleted_at", "created_at", "updated_at")
    actions = ("soft_delete_selected", "restore_selected")

    def get_queryset(self, request):
        # Admin은 감사 목적상 soft-deleted 포함 전체를 본다 (model.md §1.4).
        return Concern.objects.with_deleted().select_related("author")

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
    list_display = ("concern", "advisor", "is_active", "priority", "assigned_at")
    list_filter = ("is_active", "priority")
    search_fields = ("advisor__email", "concern__concern_summary")
    list_select_related = ("concern", "advisor", "assigned_by")
    readonly_fields = ("id", "assigned_at")
