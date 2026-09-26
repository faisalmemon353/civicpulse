import random

from app.providers.triage.base import TriageResult
from app.schemas import Category, Priority

_KEYWORD_HINTS = {
    Category.water: ["water", "pipe", "leak", "pani", "tanker"],
    Category.electricity: ["bijli", "electric", "voltage", "transformer", "meter"],
    Category.sanitation: ["garbage", "kachra", "sewerage", "sewage", "drain"],
    Category.roads: ["road", "gaddha", "pothole", "traffic", "footpath"],
    Category.streetlights: ["streetlight", "light", "khambe", "pole"],
}


class SimulatedTriage:
    """
    Deterministic, network-free triage provider used for local dev
    and CI. Supports failure injection so the fallback path can be
    tested reliably.
    """

    name = "simulated"

    def __init__(self, *, always_fail: bool = False, always_malformed: bool = False, seed: int | None = None):
        self._always_fail = always_fail
        self._always_malformed = always_malformed
        self._rng = random.Random(seed)

    def triage(self, text: str, location: str) -> TriageResult:
        if self._always_fail:
            raise RuntimeError("SimulatedTriage: forced failure for testing")

        if self._always_malformed:
            raise ValueError("SimulatedTriage: forced malformed output for testing")

        lowered = text.lower()
        category = Category.other
        for cat, keywords in _KEYWORD_HINTS.items():
            if any(kw in lowered for kw in keywords):
                category = cat
                break

        priority = self._rng.choice([Priority.high, Priority.normal, Priority.normal, Priority.low])
        summary = text[:137] + "..." if len(text) > 140 else text

        return TriageResult(
            category=category,
            priority=priority,
            summary=summary,
            confidence=round(self._rng.uniform(0.6, 0.95), 2),
        )