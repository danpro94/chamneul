"""Production settings. Secret and allowed hosts are mandatory from the env."""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403

DEBUG = False

# Fail fast if real values are not supplied by the environment.
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in _hosts.split(",") if h.strip()]
if not ALLOWED_HOSTS:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must be set in production.")

# HTTPS hardening (CLAUDE.md §10 / ADR-002).
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Mail (ADR-008, security review S-3) --------------------------------
# SMTP by default; host and credentials are wired in Phase 3. A reset mail
# carries a live link, so a backend that keeps the mail on the server (console:
# the logs, filebased: the disk) lets anyone who can read those take over the
# account. Refuse to start rather than run like that.
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
_MAIL_KEPT_ON_SERVER = (
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.filebased.EmailBackend",
)
if EMAIL_BACKEND in _MAIL_KEPT_ON_SERVER:
    raise ImproperlyConfigured(
        f"DJANGO_EMAIL_BACKEND={EMAIL_BACKEND} keeps reset links on the server; "
        "production must deliver mail."
    )

# base.py falls back to http://localhost for development, so a missing value
# fails here too (S-6): the mailed link must open the real frontend, and an
# http page can be altered in transit to read the token.
if not PASSWORD_RESET_URL.startswith("https://"):  # noqa: F405
    raise ImproperlyConfigured("PASSWORD_RESET_URL must be an https:// URL in production.")

# --- Client IP for rate limits (SPEC-006, TASK-005 security review M-1) -----
# No guessing: behind a load balancer, 0 makes every user one IP (the balancer's)
# so one attacker can use up everyone's login and signup limits; too high lets
# clients forge X-Forwarded-For. The deployment knows the number (1 behind one ALB).
if not os.environ.get("DRF_NUM_PROXIES"):
    raise ImproperlyConfigured(
        "DRF_NUM_PROXIES must be set in production: how many proxies sit in front "
        "of the app (0 if none, 1 behind one ALB)."
    )
