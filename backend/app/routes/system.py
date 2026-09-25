from fastapi import APIRouter, Response, status

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    # Deliberately does NOT touch the database — see assignment §2.2
    return {"status": "ok"}


@router.get("/ready")
def ready(response: Response):
    # TODO: replace with real Postgres + Redis checks in Step 8/9
    db_ok, cache_ok = True, True
    if not (db_ok and cache_ok):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not ready", "failed": "database" if not db_ok else "cache"}
    return {"status": "ready"}


@router.get("/metrics")
def metrics():
    # TODO: replace with real Prometheus text format in a later step
    return Response(content="# metrics placeholder\n", media_type="text/plain")