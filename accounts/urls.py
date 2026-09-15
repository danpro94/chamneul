from django.urls import path, register_converter

from . import views


class GrantableRoleConverter:
    """URL segment for a role that can be granted or revoked (ADR-003 §2).

    USER is excluded on purpose — it is the implicit default every account
    holds and is never stored as a row (model.md §3.2). Keeping it out of the
    pattern means `/roles/USER` does not resolve at all, which is what api.md
    #43 asks for: its status set has 404 but no 400.
    """

    regex = "ADMIN|ADVISOR"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(GrantableRoleConverter, "grantable_role")

# M4-1 auth (#2, #3, #4, #44) + M4-3 Google OAuth (#5, #6) + M4-2 users/me
# (#7, #8, #9, #10).
urlpatterns = [
    path("csrf", views.CsrfView.as_view(), name="csrf"),
    path("auth/signup", views.SignupView.as_view(), name="auth-signup"),
    path("auth/login", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout", views.LogoutView.as_view(), name="auth-logout"),
    path(
        "auth/google/authorize",
        views.GoogleAuthorizeView.as_view(),
        name="auth-google-authorize",
    ),
    path(
        "auth/google/callback",
        views.GoogleCallbackView.as_view(),
        name="auth-google-callback",
    ),
    path("users/me", views.UserMeView.as_view(), name="users-me"),
    path("users/me/roles", views.UserRolesView.as_view(), name="users-me-roles"),
    path("users/me/active-role", views.ActiveRoleView.as_view(), name="users-me-active-role"),
    # M4-8 admin roles (#42, #43).
    path(
        "admin/users/<uuid:user_id>/roles",
        views.AdminUserRolesView.as_view(),
        name="admin-user-roles",
    ),
    path(
        "admin/users/<uuid:user_id>/roles/<grantable_role:role>",
        views.AdminUserRoleDetailView.as_view(),
        name="admin-user-role-detail",
    ),
]
