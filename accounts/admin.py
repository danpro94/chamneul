from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm

from .models import GoogleIdentity, RoleGrant, User, UserRole


class UserCreationForm(BaseUserCreationForm):
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("email", "nickname")


class UserChangeForm(BaseUserChangeForm):
    class Meta(BaseUserChangeForm.Meta):
        model = User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User

    ordering = ("-created_at",)
    list_display = ("email", "nickname", "active_role", "is_active", "is_staff", "created_at")
    list_filter = ("is_active", "is_staff", "active_role")
    search_fields = ("email", "nickname")
    readonly_fields = ("id", "last_login", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("id", "email", "nickname", "password")}),
        ("Profile", {"fields": ("active_role", "job", "interest", "profile_image_url")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "nickname", "password1", "password2")}),
    )


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("user__email",)
    # list_display renders user per row — join it in one query (no N+1).
    list_select_related = ("user",)
    readonly_fields = ("id", "created_at")


@admin.register(RoleGrant)
class RoleGrantAdmin(admin.ModelAdmin):
    """View-only: audit rows are written by service code, never by hand
    (ADR-003 §3 — Phase 2 exposes this table through Admin for reading only).
    """

    list_display = ("user", "role", "action", "acted_by", "acted_at")
    list_filter = ("action", "role")
    search_fields = ("user__email", "acted_by__email")
    list_select_related = ("user", "acted_by")
    readonly_fields = ("id", "user", "role", "action", "acted_by", "acted_at", "reason")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(GoogleIdentity)
class GoogleIdentityAdmin(admin.ModelAdmin):
    """Rows are created by the OAuth callback (M4). Admin can inspect and
    unlink (delete); nothing is added or edited by hand (model.md §9).
    """

    list_display = ("user", "google_sub", "email")
    search_fields = ("user__email", "google_sub")
    list_select_related = ("user",)
    readonly_fields = ("id", "user", "google_sub", "email", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
