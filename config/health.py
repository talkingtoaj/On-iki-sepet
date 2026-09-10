"""Liveness endpoint for Cloud Run.

The check touches the database, because a container that has started but
cannot reach Cloud SQL is not actually able to serve, and a health check that
only proves Python is running would let that revision take traffic.
"""

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse({"status": "unavailable", "database": False}, status=503)

    return JsonResponse({"status": "ok", "database": True})
