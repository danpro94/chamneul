"""Liveness and readiness probes (ADR-010).

k8s asks two different questions. /healthz: is the process alive? (if not,
restart it). /readyz: can it serve right now? (if not, take it out of rotation
without restarting it).
"""

import logging

from django import db
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def healthz(request):
    """Liveness probe.

    Intentionally does NOT touch the database: if it did, one DB outage would
    restart every pod, and a restart does not bring the DB back (ADR-010).
    """
    return JsonResponse({"status": "ok"})


def readyz(request):
    """Readiness probe — 200 when the database answers, 503 when it does not.

    The cause goes to the server log only. The exception text names the DB
    host, address and port, so the body stays fixed (CLAUDE.md §8).
    """
    try:
        with db.connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except db.Error as exc:
        logger.warning("readyz: database unavailable (%s: %s)", type(exc).__name__, exc)
        return JsonResponse(
            {"status": "unavailable", "checks": {"database": "unavailable"}}, status=503
        )
    return JsonResponse({"status": "ok", "checks": {"database": "ok"}})


_PROBES = {"/healthz": healthz, "/readyz": readyz}


class HealthCheckMiddleware:
    """Answers the two probe paths ahead of the HTTPS redirect and host check.

    kubelet and the ALB call http://<pod-ip>:8000/healthz — plain HTTP, with a
    Host that is not in ALLOWED_HOSTS. Further down that is a 301
    (SECURE_SSL_REDIRECT) or a 400 (DisallowedHost), and a probe that never
    sees 200 takes the pod out. Only an exact path with GET/HEAD skips those
    checks; both views return fixed bodies that never use the Host.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        probe = _PROBES.get(request.path_info)
        if probe is not None and request.method in ("GET", "HEAD"):
            return probe(request)
        return self.get_response(request)
