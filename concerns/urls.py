from django.urls import path

from . import views

# M4-5 concerns (SPEC-001). #16 (POST) and #17 (GET) share one path;
# #18 (GET) and #19 (DELETE) share the /{concern-id} path. #20/#21 are the
# advisor-side counterpart under /assigned-concerns.
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
    path(
        "users/me/assigned-concerns",
        views.AssignedConcernListView.as_view(),
        name="users-me-assigned-concerns",
    ),
    path(
        "users/me/assigned-concerns/<uuid:concern_id>",
        views.AssignedConcernDetailView.as_view(),
        name="users-me-assigned-concern-detail",
    ),
    path(
        "admin/concerns",
        views.AdminConcernListView.as_view(),
        name="admin-concerns",
    ),
    path(
        "admin/concerns/<uuid:concern_id>",
        views.AdminConcernDetailView.as_view(),
        name="admin-concern-detail",
    ),
    path(
        "admin/concerns/<uuid:concern_id>/assignments",
        views.AdminAssignmentCreateView.as_view(),
        name="admin-concern-assignments",
    ),
    path(
        "admin/concerns/<uuid:concern_id>/assignments/<uuid:assignment_id>",
        views.AdminAssignmentDetailView.as_view(),
        name="admin-concern-assignment-detail",
    ),
]
