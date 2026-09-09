from django.urls import path

from . import views

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
]
