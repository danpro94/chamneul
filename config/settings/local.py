"""Local development settings."""

from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# http://localhost is not HTTPS, so Secure cookies would never be sent back.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Mail delivery is Phase 3 (ADR-008): reset links are printed to the app's
# stdout instead — read them with `docker compose logs app`.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
