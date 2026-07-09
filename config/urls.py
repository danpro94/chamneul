from django.contrib import admin
from django.urls import include, path

from .health import healthz

urlpatterns = [
    # Unversioned liveness endpoint (CLAUDE.md §7: only /healthz is unversioned).
    path("healthz", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    # All versioned APIs live under /api/v1/ (CLAUDE.md §7).
    path("api/v1/", include("accounts.urls")),
]
