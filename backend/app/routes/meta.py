from fastapi import APIRouter

from app import triage_log
from app.providers.triage.factory import get_active_provider

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/providers")
def get_providers():
    """
    Returns the currently active triage provider and a rolling window
    of the last 20 triage outcomes (provider name, latency_ms,
    is_fallback, recorded_at).

    Storage: in-memory deque — resets on restart, which is acceptable
    because this endpoint is a live operational dashboard, not a
    persistent audit log.  Outcomes accumulate from the first POST
    /api/complaints after server start.
    """
    active_provider = get_active_provider()
    return {
        "active_provider": active_provider.name,
        "recent_outcomes": triage_log.recent(),
    }