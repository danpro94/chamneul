"""Test settings — still PostgreSQL (CLAUDE.md §4: SQLite is never used)."""

from .base import *  # noqa: F401,F403

# Faster hashing; the test database is disposable so strength is irrelevant.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# No EMAIL_BACKEND here on purpose: Django's test runner always swaps in the
# locmem backend, so sent mail lands in `django.core.mail.outbox`.
