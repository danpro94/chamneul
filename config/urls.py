from django.contrib import admin
from django.urls import path

from .health import healthz

urlpatterns = [
    # Unversioned liveness endpoint (CLAUDE.md §7: only /healthz is unversioned).
    path("healthz", healthz, name="healthz"),
    path("admin/", admin.site.urls),
]
