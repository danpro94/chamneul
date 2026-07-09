from rest_framework.authentication import SessionAuthentication


class CsrfSessionAuthentication(SessionAuthentication):
    """SessionAuthentication that reports 401 (not 403) for anonymous requests.

    DRF downgrades NotAuthenticated (401) to 403 when no authenticator returns a
    `WWW-Authenticate` header. Our permission matrix (api.md, CLAUDE.md §10)
    needs the honest distinction: 401 = not logged in, 403 = logged in but not
    allowed. Returning a header value restores the 401 for unauthenticated
    requests. CSRF enforcement (inherited) is unchanged.
    """

    def authenticate_header(self, request):
        return "Session"
