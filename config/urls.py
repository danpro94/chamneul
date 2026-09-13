from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from .health import healthz

urlpatterns = [
    # Unversioned liveness endpoint (CLAUDE.md §7: only /healthz is unversioned).
    path("healthz", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    # All versioned APIs live under /api/v1/ (CLAUDE.md §7).
    path("api/v1/", include("accounts.urls")),
    path("api/v1/", include("advisors.urls")),
    path("api/v1/", include("concerns.urls")),
    path("api/v1/", include("advice.urls")),
]

if settings.DEBUG:
    # Login/logout for DRF's Browsable API only — lets the Owner sign in with a
    # real browser and visually exercise the API (forms + rendered lists)
    # without a separate frontend. Never enabled outside DEBUG (CLAUDE.md §10).
    urlpatterns += [
        path("api-auth/", include("rest_framework.urls")),
    ]
