from functools import lru_cache

from app.config import settings
from app.providers.triage.base import TriageProvider
from app.providers.triage.llm import LLMTriage
from app.providers.triage.ollama import OllamaTriage
from app.providers.triage.rules import RuleBasedTriage
from app.providers.triage.simulated import SimulatedTriage


@lru_cache
def get_active_provider() -> TriageProvider:
    provider_name = settings.triage_provider

    if provider_name == "simulated":
        return SimulatedTriage()
    if provider_name == "rules":
        return RuleBasedTriage()
    if provider_name in ("llm", "openrouter", "llm:openrouter"):
        return LLMTriage()
    if provider_name in ("ollama", "llm:ollama"):
        return OllamaTriage()

    return RuleBasedTriage()