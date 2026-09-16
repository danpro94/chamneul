from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """View-only (SPEC-003 리뷰 S-4).

    Rows are side effects of service code (§6.4), never written by hand. Two
    fields in particular must not be editable: `recipient`, because moving a
    notification to another account would show them someone else's data through
    #39/#40; and `read_at`, because #41 treats "when the user first saw this"
    as an invariant and deliberately never overwrites it.
    """

    list_display = ("recipient", "type", "is_read", "created_at")
    list_filter = ("type", "is_read")
    search_fields = ("recipient__email", "title")
    list_select_related = ("recipient", "actor_user")
    readonly_fields = (
        "id",
        "recipient",
        "type",
        "title",
        "message",
        "target_url",
        "actor_user",
        "payload",
        "is_read",
        "read_at",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
