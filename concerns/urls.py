from django.urls import path

from . import views

# M4-5 concerns (SPEC-001). #16 (POST) and #17 (GET) share this one path.
urlpatterns = [
    path(
        "users/me/concerns",
        views.ConcernListCreateView.as_view(),
        name="users-me-concerns",
    ),
]
