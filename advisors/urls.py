from django.urls import path

from . import views

# M4-4 advisor applications (api.md #11-15).
urlpatterns = [
    path(
        "advisor-applications",
        views.AdvisorApplicationView.as_view(),
        name="advisor-applications",
    ),
    path(
        "advisor-applications/me",
        views.AdvisorApplicationMeView.as_view(),
        name="advisor-applications-me",
    ),
    path(
        "admin/advisor-applications",
        views.AdminAdvisorApplicationListView.as_view(),
        name="admin-advisor-applications",
    ),
    path(
        "admin/advisor-applications/<uuid:application_id>",
        views.AdminAdvisorApplicationDetailView.as_view(),
        name="admin-advisor-application-detail",
    ),
]
