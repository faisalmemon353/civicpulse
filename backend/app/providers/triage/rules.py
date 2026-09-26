from app.providers.triage.base import TriageResult
from app.schemas import Category, Priority

_KEYWORD_MAP = {
    Category.water: ["water", "pipe", "leak", "tanker", "pani"],
    Category.electricity: ["bijli", "electric", "voltage", "transformer", "meter", "power"],
    Category.sanitation: ["garbage", "kachra", "sewerage", "sewage", "drain", "trash"],
    Category.roads: ["road", "gaddha", "pothole", "traffic", "footpath", "street "],
    Category.streetlights: ["streetlight", "light", "khambe", "pole", "lamp"],
}

_URGENT_KEYWORDS = ["flooding", "spark", "accident", "danger", "khatra", "urgent", "emergency"]


class RuleBasedTriage:
    """
    Deterministic keyword-based triage. Must never raise — this is
    the last line of defense when the LLM provider fails.
    """

    name = "rules"

    def triage(self, text: str, location: str) -> TriageResult:
        lowered = text.lower()

        category = Category.other
        for cat, keywords in _KEYWORD_MAP.items():
            if any(kw in lowered for kw in keywords):
                category = cat
                break

        priority = Priority.high if any(kw in lowered for kw in _URGENT_KEYWORDS) else Priority.normal
        summary = text[:137] + "..." if len(text) > 140 else text

        return TriageResult(category=category, priority=priority, summary=summary, confidence=0.5)