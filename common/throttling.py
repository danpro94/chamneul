"""Request rate limits for the anonymous auth endpoints (SPEC-006 TASK-001).

Counters live in the shared cache (settings.CACHES — a PostgreSQL table), so
every gunicorn worker and pod counts against the same numbers. The numbers
themselves are one table: REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].
"""

from collections.abc import Mapping

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.utils.crypto import salted_hmac
from rest_framework.settings import api_settings
from rest_framework.throttling import SimpleRateThrottle


def pseudonymize(value: str) -> str:
    """Counter key for an email or IP, so the cache table holds neither.

    A plain sha256 of an address is reversed by hashing candidate addresses;
    keyed with SECRET_KEY, the table alone reveals nothing.
    """
    return salted_hmac("common.throttling", value, algorithm="sha256").hexdigest()


class _RateFromSettings(SimpleRateThrottle):
    def get_rate(self):
        # DRF copies DEFAULT_THROTTLE_RATES into a class attribute at import
        # time, so later settings changes (and override_settings in tests)
        # never reach it. Read the table on every request instead.
        try:
            return api_settings.DEFAULT_THROTTLE_RATES[self.scope]
        except KeyError:
            raise ImproperlyConfigured(f"No throttle rate for scope {self.scope!r}") from None


class IPRateThrottle(_RateFromSettings):
    """Counts per client IP. DRF's get_ident() trusts exactly NUM_PROXIES
    X-Forwarded-For hops (0 locally: the header is ignored)."""

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": pseudonymize(self.get_ident(request)),
        }


class EmailRateThrottle(_RateFromSettings):
    """Counts per submitted address, normalised exactly like the account
    lookup, so case variants share one counter.

    It counts the string the caller typed, never whether an account exists —
    the 429 is the same either way (ADR-008 §2).
    """

    def get_cache_key(self, request, view):
        # No local holds request.data: this runs before the view, outside its
        # sensitive_variables(), so a crash report would print it — password
        # included.
        email = request.data.get("email") if isinstance(request.data, Mapping) else None
        if not isinstance(email, str):
            # Nothing to count. The IP limit still applies; the serializer
            # answers the 400.
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": pseudonymize(get_user_model().objects.canonical_email(email)),
        }


# DRF builds throttles without arguments, so each scope is its own class.
# accounts/views.py attaches them; the numbers stay in settings.


class SignupIPThrottle(IPRateThrottle):
    scope = "auth_signup_ip"


class LoginIPThrottle(IPRateThrottle):
    scope = "auth_login_ip"


class LoginEmailThrottle(EmailRateThrottle):
    scope = "auth_login_email"


class PasswordResetIPThrottle(IPRateThrottle):
    scope = "password_reset_ip"


class PasswordResetEmailThrottle(EmailRateThrottle):
    scope = "password_reset_email"


class PasswordResetConfirmIPThrottle(IPRateThrottle):
    scope = "password_reset_confirm_ip"
