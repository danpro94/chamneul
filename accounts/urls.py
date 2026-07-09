from django.urls import path

from . import views

# M4-1 auth surface (api.md #2, #3, #4, #44). Users/me and OAuth land in
# M4-2 / M4-3 and will extend this list.
urlpatterns = [
    path("csrf", views.CsrfView.as_view(), name="csrf"),
    path("auth/signup", views.SignupView.as_view(), name="auth-signup"),
    path("auth/login", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout", views.LogoutView.as_view(), name="auth-logout"),
]
