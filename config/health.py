from django.http import JsonResponse


def healthz(request):
    """Liveness probe.

    Intentionally does NOT touch the database so it stays green even during a
    DB outage — it answers only "is the app process up?". A DB-aware readiness
    probe (`/healthz/db`) is a deliberate follow-up (see docs/reviews/01).
    """
    return JsonResponse({"status": "ok"})
