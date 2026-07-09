import secrets

from django.conf import settings
from django.contrib.auth import login, logout
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import Conflict

from . import oauth, services
from .serializers import (
    ActiveRoleSerializer,
    LoginSerializer,
    SignupResultSerializer,
    SignupSerializer,
    UserCardSerializer,
    UserMeSerializer,
    UserUpdateResultSerializer,
    UserUpdateSerializer,
)

# Anonymous state-changing endpoints (signup/login) still require CSRF (ADR-002
# §5). DRF's SessionAuthentication only enforces CSRF for *authenticated*
# requests, and DRF marks APIViews csrf_exempt at the middleware layer — so for
# anonymous POSTs we re-assert the check explicitly with csrf_protect.
# Authenticated PATCH/POST/DELETE below are CSRF-checked by SessionAuthentication.
csrf_protected = method_decorator(csrf_protect, name="dispatch")

# OAuth-specific error responses (api.md #6 status set).
OAUTH_STATE_COOKIE = "oauth_state"


class _BadGateway(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Google 인증 서버와 통신하지 못했습니다."
    default_code = "bad_gateway"


class _AuthFailed(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Google 인증 검증에 실패했습니다."
    default_code = "google_auth_failed"


class _OAuthUnavailable(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Google 로그인이 구성되지 않았습니다."
    default_code = "oauth_unconfigured"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """GET /api/v1/csrf (#44) — CSRF bootstrap.

    Sets the `csrftoken` cookie so a not-yet-logged-in client can make its first
    state-changing request (login/signup). Read-only, so it is not itself CSRF
    protected. Issues no session.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"detail": "CSRF cookie set"})


@csrf_protected
class SignupView(APIView):
    """POST /api/v1/auth/signup (#2) — create account and auto-login (ADR-002 §9)."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # Issue the session immediately — the response carries Set-Cookie: sessionid.
        login(request, user)
        return Response(SignupResultSerializer(user).data, status=status.HTTP_201_CREATED)


@csrf_protected
class LoginView(APIView):
    """POST /api/v1/auth/login (#3) — email/password login, issues the session."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        # api.md #3: response wraps the identity card under `user`.
        return Response({"user": UserCardSerializer(user).data}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """POST /api/v1/auth/logout (#4) — server-side session flush + cookie clear.

    `logout()` deletes the server session record and clears the cookie; we do
    not rely on client-side deletion (ADR-002 §4). SessionAuthentication
    enforces CSRF here because the request is authenticated.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"message": "로그아웃 되었습니다."}, status=status.HTTP_200_OK)


class GoogleAuthorizeView(APIView):
    """GET /api/v1/auth/google/authorize (#5) — 302 to Google consent screen.

    A random `state` is set as an HttpOnly cookie and echoed in the redirect;
    the callback compares the two (CSRF for OAuth). No session is created here.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        if not oauth.is_configured():
            raise _OAuthUnavailable()
        state = secrets.token_urlsafe(32)
        response = HttpResponseRedirect(oauth.build_authorize_url(state))
        response.set_cookie(
            OAUTH_STATE_COOKIE,
            state,
            max_age=600,
            httponly=True,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite="Lax",
        )
        return response


class GoogleCallbackView(APIView):
    """GET /api/v1/auth/google/callback (#6) — verify, link/create, issue session.

    state mismatch -> 400, upstream/Google failure -> 502, token verify failure
    -> 401. On success: same session model as email login (ADR-002 §7), 302 to
    the frontend entry.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        if request.query_params.get("error"):
            # User denied consent, or Google returned an error.
            raise ValidationError("Google 로그인이 취소되었거나 실패했습니다.")

        state = request.query_params.get("state")
        cookie_state = request.COOKIES.get(OAUTH_STATE_COOKIE)
        # Constant-time compare; empty/missing values must not match.
        if not state or not cookie_state or not secrets.compare_digest(state, cookie_state):
            raise ValidationError("state 검증에 실패했습니다.")

        code = request.query_params.get("code")
        if not code:
            raise ValidationError("인가 코드가 없습니다.")

        try:
            id_token = oauth.exchange_code_for_id_token(code)
            claims = oauth.verify_id_token(id_token)
        except oauth.OAuthConfigError as exc:
            raise _OAuthUnavailable() from exc
        except oauth.OAuthVerifyError as exc:
            raise _AuthFailed() from exc
        except oauth.OAuthUpstreamError as exc:
            raise _BadGateway() from exc

        user = services.link_or_create_google_user(
            google_sub=claims["sub"],
            email=claims["email"],
            name=claims.get("name", ""),
        )
        # The email/password path gates on is_active via authenticate(); OAuth
        # skips authenticate(), so gate here too (S1 — required before any
        # account-deactivation feature; no such state exists in Phase 2 yet).
        if not user.is_active:
            raise _AuthFailed()
        login(request, user)

        response = HttpResponseRedirect(settings.GOOGLE_OAUTH_SUCCESS_REDIRECT)
        response.delete_cookie(OAUTH_STATE_COOKIE)
        return response


class UserMeView(APIView):
    """GET/PATCH /api/v1/users/me (#7, #8) — read / partial-update own profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserMeSerializer(request.user).data)

    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
        except IntegrityError as exc:
            # validate_nickname pre-checks, but a concurrent request can still win
            # the unique race — the DB constraint is the final arbiter (S8).
            raise Conflict("이미 사용 중인 닉네임입니다.") from exc
        return Response(UserUpdateResultSerializer(request.user).data)


class UserRolesView(APIView):
    """GET /api/v1/users/me/roles (#9) — held roles + active role + advisor status."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "roles": services.held_roles(user),
                "active_role": user.active_role,
                "advisor_status": services.advisor_status(user),
            }
        )


class ActiveRoleView(APIView):
    """PATCH /api/v1/users/me/active-role (#10) — switch to a held role."""

    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = ActiveRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        services.set_active_role(user, serializer.validated_data["active_role"])
        return Response(
            {
                "user_id": str(user.id),
                "active_role": user.active_role,
                "roles": services.held_roles(user),
            }
        )
