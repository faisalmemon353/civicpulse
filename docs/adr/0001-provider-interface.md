# ADR 0001: Replaceable AI Triage Provider via Strategy Pattern

## Status
Accepted

## Context
CivicPulse ingests unstructured citizen complaint text and must classify each into a validated operational category (`water`, `electricity`, `sanitation`, `roads`, `streetlights`, `other`), assign an urgency priority (`high`, `normal`, `low`), and generate a concise one-line executive summary ($\le 140$ characters).

In production and testing, inference requirements differ drastically:
1. Production cloud deployments benefit from fast, hosted LLMs (e.g., Groq, OpenRouter).
2. Offline, air-gapped, or privacy-critical local deployments require a self-hosted open-weights model (e.g., Ollama running `llama3.2:1b`).
3. Automated CI pipelines need fast, deterministic, zero-network tests with configurable failure injection.
4. If an external model is rate-limited (HTTP 429), unavailable (HTTP 5xx), or times out, the system must never drop or fail citizen submissions.

## Decision
We implement a pluggable Strategy pattern using Python's `typing.Protocol` defining a unified `TriageProvider` contract:

```python
class TriageResult(BaseModel):
    category: Category
    priority: Priority
    summary: str = Field(max_length=140)
    confidence: float = Field(ge=0.0, le=1.0)

class TriageProvider(Protocol):
    name: str
    def triage(self, text: str, location: str) -> TriageResult: ...
```

Four concrete implementations satisfy this protocol, selected dynamically by the `TRIAGE_PROVIDER` environment variable via `app.providers.triage.factory.get_active_provider()`:
1. `LLMTriage` (`llm:openrouter`): Calls hosted OpenAI-compatible chat completion APIs with structured JSON output enforcement.
2. `OllamaTriage` (`llm:ollama`): Fully offline path targeting a local Ollama container (`llama3.2:1b`), caching results in Redis.
3. `SimulatedTriage` (`simulated`): Fast deterministic fake for CI and unit tests, with optional seed and configurable failure injection.
4. `RuleBasedTriage` (`rules` / `rules:fallback`): Zero-dependency heuristic keyword matcher providing an unbreakable fallback when primary AI providers fail or time out.

## Justification & Tradeoffs
- **Decoupling:** Business routes depend purely on the protocol abstraction, never on vendor SDKs or concrete HTTP clients.
- **Fail-Safe Resilience:** When the primary provider encounters network partition, timeout (hard cap), or JSON validation failure, execution automatically degrades to `RuleBasedTriage` and records `triaged_by = "rules:fallback"` without returning HTTP 500 to citizens.
- **Cost & Latency Optimization:** Both `LLMTriage` and `OllamaTriage` check a content-hash key in Redis (`triage:sha256(text)`), ensuring duplicate complaints are resolved in $\le 2$ ms with zero redundant tokens consumed.
