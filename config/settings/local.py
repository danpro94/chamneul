"""Local development settings."""
from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# http://localhost is not HTTPS, so Secure cookies would never be sent back.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
