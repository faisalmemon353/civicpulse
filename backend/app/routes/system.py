from fastapi import APIRouter, Response, status

from app.cache import check_redis
from app.db import check_postgres
from app.metrics import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    """
    Liveness probe.
    Deliberately does NOT touch the database or cache — verifies that the
    application process is alive and responsive to HTTP requests.
    """
    return {"status": "ok"}


@router.get("/ready")
def ready(response: Response):
    """
    Readiness probe.
    Verifies that all external dependencies (Postgres and Redis) are reachable.
    Returns 503 Service Unavailable naming the failed dependency if either is down.
    """
    db_ok = check_postgres()
    cache_ok = check_redis()

    if not (db_ok and cache_ok):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        failed = []
        if not db_ok:
            failed.append("database")
        if not cache_ok:
            failed.append("cache")
        return {
            "status": "not ready",
            "failed": ", ".join(failed),
            "checks": {"database": db_ok, "cache": cache_ok},
        }

    return {
        "status": "ready",
        "checks": {"database": True, "cache": True},
    }


@router.get("/metrics")
def metrics():
    """Prometheus metrics exposition endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
