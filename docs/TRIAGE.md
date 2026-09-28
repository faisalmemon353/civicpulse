# CivicPulse AI Triage Layer Specification (§2.5)

## Overview
CivicPulse automates the intake, classification, and summarization of municipal citizen complaints using a replaceable Strategy-pattern triage engine.

---

## 1. Provider Implementations

| Provider Name | Class | Configuration (`TRIAGE_PROVIDER`) | Description |
| :--- | :--- | :--- | :--- |
| `llm:openrouter` | `LLMTriage` | `llm` / `openrouter` | Hosted OpenAI-compatible cloud LLM with JSON mode enforcement. |
| `llm:ollama` | `OllamaTriage` | `ollama` / `llm:ollama` | On-premise offline model (`llama3.2:1b`) running in Docker. |
| `simulated` | `SimulatedTriage`| `simulated` | Seeded deterministic fake for unit tests and CI pipelines. |
| `rules:fallback`| `RuleBasedTriage` | `rules` / automatic fallback | Zero-dependency heuristic keyword classifier. |

---

## 2. Resilience & Circuit Breaker Logic
1. **Timeout Cap:** Every AI inference request enforces a strict timeout cap.
2. **Jittered Retry:** A single retry with randomized backoff is attempted exclusively on retryable errors (HTTP 429, 5xx, or network timeouts). Client errors (HTTP 4xx) fail immediately.
3. **Graceful Fallback:** If the primary AI provider fails, throws an exception, or times out, execution seamlessly falls back to `RuleBasedTriage`. The response records:
   ```json
   "triaged_by": "rules:fallback"
   ```
   and emits a `WARNING`-level structured log to stdout. The citizen receives HTTP 201 Created and never an HTTP 500 server error.

---

## 3. Caching Strategy
- **Mechanism:** SHA-256 hash of normalized complaint text: `triage:ollama:<sha256_hash>`.
- **TTL:** 24 hours in Redis.
- **Performance:** Duplicate citizen submissions bypass LLM inference completely, returning a validated `TriageResult` in $\le 2\text{ ms}$ with zero token consumption.

---

## 4. Prompt Injection Defense
Unsanitized user complaints are treated strictly as untrusted data:
```python
user_prompt = f'Complaint text: """{text}"""\nLocation: {location}'
```
All model outputs are deserialized and strictly validated against the Pydantic `TriageResult` model, rejecting non-conforming responses or prompt jailbreak attempts.
