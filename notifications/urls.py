from django.urls import path

from . import views

# M4-7 notifications (#39, #40). #41 (read) arrives in TASK-002.
urlpatterns = [
    path("notifications", views.NotificationListView.as_view(), name="notifications"),
    path(
        "notifications/<uuid:notification_id>",
        views.NotificationDetailView.as_view(),
        name="notification-detail",
    ),
]
