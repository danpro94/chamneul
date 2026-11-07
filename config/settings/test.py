"""Test settings — still PostgreSQL (CLAUDE.md §4: SQLite is never used)."""

from .base import *  # noqa: F401,F403

# Faster hashing; the test database is disposable so strength is irrelevant.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Tests never run collectstatic: there is no manifest of hashed names (any
# {% static %} would raise with DEBUG=False) and no STATIC_ROOT folder (WhiteNoise
# would warn on every test client). config.tests.StaticFilesTests serves
# straight from the apps' static folders instead.
STORAGES = {
    **STORAGES,  # noqa: F405
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
STATIC_ROOT = None

# No EMAIL_BACKEND here on purpose: Django's test runner always swaps in the
# locmem backend, so sent mail lands in `django.core.mail.outbox`.

# Rate limits stay wired (counters still hit the cache table) but out of reach:
# one test may log in or ask for a reset more often than the real table allows.
# accounts.tests.RateLimitTests sets its own small numbers.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": dict.fromkeys(
        REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],  # noqa: F405
        "10000/min",
    ),
}
