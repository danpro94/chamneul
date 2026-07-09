"""Google OAuth helpers — standard library only (D-5: no third-party package).

The callback verifies the ID token via Google's tokeninfo endpoint. That costs
one extra HTTPS round trip per login (Owner accepted this in D-5); the
production-grade upgrade is local signature verification against Google's certs
(a Phase 3 follow-up). All network targets are fixed constants (no SSRF surface)
and every call has a timeout.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"

_HTTP_TIMEOUT = 10


class OAuthError(Exception):
    """Base for OAuth failures."""


class OAuthConfigError(OAuthError):
    """Client id/secret not configured."""


class OAuthUpstreamError(OAuthError):
    """Google returned an error or was unreachable (maps to 502)."""


class OAuthVerifyError(OAuthError):
    """ID token failed verification — audience/email (maps to 401)."""


def is_configured() -> bool:
    return bool(settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET)


def build_authorize_url(state: str) -> str:
    """Google consent-screen URL (api.md #5). `state` ties the callback back to
    this request (CSRF for OAuth)."""
    if not is_configured():
        raise OAuthConfigError("Google OAuth is not configured")
    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def _post_json(url: str, data: dict) -> dict:
    body = urllib.parse.urlencode(data).encode()
    request = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise OAuthUpstreamError(f"token endpoint failed: {exc}") from exc


def _get_json(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=_HTTP_TIMEOUT) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise OAuthUpstreamError(f"tokeninfo endpoint failed: {exc}") from exc


def exchange_code_for_id_token(code: str) -> str:
    """Authorization code -> ID token (api.md #6)."""
    if not is_configured():
        raise OAuthConfigError("Google OAuth is not configured")
    payload = _post_json(
        GOOGLE_TOKEN_URL,
        {
            "code": code,
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    )
    id_token = payload.get("id_token")
    if not id_token:
        raise OAuthUpstreamError("token response missing id_token")
    return id_token


def verify_id_token(id_token: str) -> dict:
    """Verify via tokeninfo and return claims. tokeninfo checks signature/expiry;
    we still must confirm the token was minted for *us* (audience) and that the
    email is verified before trusting it.
    """
    claims = _get_json(f"{GOOGLE_TOKENINFO_URL}?{urllib.parse.urlencode({'id_token': id_token})}")
    if claims.get("aud") != settings.GOOGLE_OAUTH_CLIENT_ID:
        raise OAuthVerifyError("id_token audience mismatch")
    if str(claims.get("email_verified")).lower() != "true":
        raise OAuthVerifyError("email not verified by Google")
    if not claims.get("email") or not claims.get("sub"):
        raise OAuthVerifyError("id_token missing email/sub")
    return claims
