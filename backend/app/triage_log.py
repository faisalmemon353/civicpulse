"""
triage_log.py
=============
In-memory rolling window of the last 20 triage outcomes.

Design decision:
    An in-memory deque is used instead of Redis because this is
    explicitly a non-persistent rolling audit window (resets on
    restart is acceptable per the spec).  Adding Redis here would
    introduce a network dependency and serialisation overhead for
    ephemeral data.  If persistence is required later the interface
    stays the same — only this module changes.

Thread safety:
    deque.append() and list(deque) are both atomic in CPython due to
    the GIL.  Under an ASGI worker (single-threaded event loop per
    process) this is sufficient.  Under multiple Uvicorn workers each
    process has its own deque — acceptable for a rolling window that
    resets on restart.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime

MAX_OUTCOMES = 20


@dataclass
class TriageOutcome:
    provider: str          # e.g. "simulated", "llm:openrouter", "rules:fallback"
    latency_ms: int
    is_fallback: bool
    recorded_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def as_dict(self) -> dict:
        return {
            "provider": self.provider,
            "latency_ms": self.latency_ms,
            "is_fallback": self.is_fallback,
            "recorded_at": self.recorded_at,
        }


# Module-level singleton — intentionally not a class instance so
# there is no import-time side effect beyond the deque allocation.
_outcomes: deque[TriageOutcome] = deque(maxlen=MAX_OUTCOMES)


def record(provider: str, latency_ms: int, is_fallback: bool) -> None:
    """Append one outcome to the rolling window."""
    _outcomes.append(TriageOutcome(provider=provider, latency_ms=latency_ms, is_fallback=is_fallback))


def recent() -> list[dict]:
    """Return the last ≤20 outcomes, most-recent last."""
    return [o.as_dict() for o in _outcomes]


def clear() -> None:
    """Empty the window.  Used by tests to prevent cross-test pollution."""
    _outcomes.clear()
