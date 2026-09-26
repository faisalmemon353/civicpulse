import json
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.cache import get_redis_client
from app.db import get_db
from app.repositories.complaints import get_complaint_stats

router = APIRouter(prefix="/api", tags=["stats"])

STATS_CACHE_KEY = "stats:aggregates"
STATS_CACHE_TTL_SECONDS = 30


def invalidate_stats_cache() -> None:
    """Invalidates the cached stats aggregates in Redis."""
    client = get_redis_client()
    if client:
        try:
            client.delete(STATS_CACHE_KEY)
        except Exception:
            pass


@router.get("/stats")
def get_stats(response: Response, db: Session = Depends(get_db)):
    client = get_redis_client()
    cached = None
    if client:
        try:
            cached = client.get(STATS_CACHE_KEY)
        except Exception:
            cached = None

    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        try:
            return json.loads(cached)
        except Exception:
            pass

    response.headers["X-Cache"] = "MISS"
    stats_data = get_complaint_stats(db)

    if client:
        try:
            client.set(STATS_CACHE_KEY, json.dumps(stats_data), ex=STATS_CACHE_TTL_SECONDS)
        except Exception:
            pass

    return stats_data