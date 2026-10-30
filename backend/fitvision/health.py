"""Lightweight liveness / readiness endpoints for deployments and monitoring."""

import logging

from django.core.cache import cache
from django.db import connection
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def _database_ok() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except Exception:
        logger.exception("Database health check failed")
        return False


def _cache_ok() -> bool:
    try:
        cache.set("fitvision:health", "ok", timeout=5)
        return cache.get("fitvision:health") == "ok"
    except Exception:
        logger.exception("Cache health check failed")
        return False


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Return 200 when the app can reach its database (and cache, if configured)."""
    checks = {"database": _database_ok(), "cache": _cache_ok()}
    healthy = all(checks.values())
    return Response(
        {
            "status": "ok" if healthy else "degraded",
            "checks": checks,
        },
        status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_index(request):
    """Small discovery document for humans and simple clients."""
    return Response(
        {
            "name": "FitVision API",
            "version": "1.0.0",
            "docs": request.build_absolute_uri("/api/docs/"),
            "schema": request.build_absolute_uri("/api/schema/"),
            "health": request.build_absolute_uri("/api/health/"),
        }
    )
