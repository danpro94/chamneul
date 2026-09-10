from django.urls import path

from . import views

# M4-5 concerns (SPEC-001). #16 (POST) and #17 (GET) share one path;
# #18 (GET) and #19 (DELETE) share the /{concern-id} path.
urlpatterns = [
    path(
        "users/me/concerns",
        views.ConcernListCreateView.as_view(),
        name="users-me-concerns",
    ),
    path(
        "users/me/concerns/<uuid:concern_id>",
        views.ConcernDetailView.as_view(),
        name="users-me-concern-detail",
    ),
]
