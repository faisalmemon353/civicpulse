from functools import lru_cache

from app.config import settings
from app.providers.triage.base import TriageProvider
from app.providers.triage.rules import RuleBasedTriage
from app.providers.triage.simulated import SimulatedTriage


@lru_cache
def get_active_provider() -> TriageProvider:
    """
    Returns the configured triage provider, chosen via TRIAGE_PROVIDER
    in .env. @lru_cache means this only actually constructs the
    provider once per process, not on every request.
    """
    provider_name = settings.triage_provider

    if provider_name == "simulated":
        return SimulatedTriage()
    if provider_name == "rules":
        return RuleBasedTriage()

    # llm and ollama providers are added in a later step —
    # for now, fall back to rules if something else is configured.
    return RuleBasedTriage()