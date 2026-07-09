from django.contrib.auth import login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
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


class UserMeView(APIView):
    """GET/PATCH /api/v1/users/me (#7, #8) — read / partial-update own profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserMeSerializer(request.user).data)

    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
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
