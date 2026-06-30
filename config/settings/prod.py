"""Production settings. Secret and allowed hosts are mandatory from the env."""
import os

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
