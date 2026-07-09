from django.contrib.auth import login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginSerializer, SignupSerializer, UserMeSerializer

# Anonymous state-changing endpoints (signup/login) still require CSRF (ADR-002
# §5). DRF's SessionAuthentication only enforces CSRF for *authenticated*
# requests, and DRF marks APIViews csrf_exempt at the middleware layer — so for
# anonymous POSTs we re-assert the check explicitly with csrf_protect.
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
        return Response(UserMeSerializer(user).data, status=status.HTTP_201_CREATED)


@csrf_protected
class LoginView(APIView):
    """POST /api/v1/auth/login (#3) — email/password login, issues the session."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        return Response(UserMeSerializer(user).data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """POST /api/v1/auth/logout (#4) — server-side session flush + cookie clear.

    `logout()` deletes the server session record and clears the cookie; we do
    not rely on client-side deletion (ADR-002 §4). SessionAuthentication
    enforces CSRF here because the request is authenticated.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
