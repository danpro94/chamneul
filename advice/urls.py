from django.urls import path

from . import views

# M4-6 advice + feedback (SPEC-002). TASK-001: #28 (author), #31 (own list).
urlpatterns = [
    path(
        "concerns/<uuid:concern_id>/advices",
        views.AdviceCreateView.as_view(),
        name="concern-advices",
    ),
    path(
        "users/me/advices-written",
        views.AdvicesWrittenView.as_view(),
        name="users-me-advices-written",
    ),
    path(
        "advices/<uuid:advice_id>",
        views.AdviceDetailView.as_view(),
        name="advice-detail",
    ),
]
