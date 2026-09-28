# ADR 0004: Personally Identifiable Information (PII) and Data Governance

## Status
Accepted

## Context
Municipal citizen complaints frequently contain sensitive Personally Identifiable Information (PII), including citizen names, phone numbers, exact residential street addresses, landmark references, or CNIC numbers. 

When leveraging artificial intelligence for automated triage, sending citizen raw input to public or third-party hosted LLM endpoints (e.g., Google AI Studio free tier, Groq, OpenRouter) creates regulatory, privacy, and security liabilities. Notably, certain free-tier cloud API agreements permit vendors to retain and inspect input prompts for model training.

## Decision
We establish a multi-tier data privacy and governance policy enforced across the application lifecycle:

1. **Isolation of Reporter Contact Data:**
   - The citizen contact field (`reporter_contact`) is **never** passed to any AI model or prompt template. Only `text` (incident description) and `location` (general vicinity) are sent to the triage provider.
   - Contact details are stored exclusively in the isolated PostgreSQL database on the `internal` Docker network.

2. **Zero-Dependency Local Inference Option (Ollama):**
   - For environments handling strict sovereign citizen data or offline scenarios, `TRIAGE_PROVIDER=ollama` runs `llama3.2:1b` entirely on-premise within the container perimeter. Zero bits of citizen text or metadata leave the host machine.

3. **Prompt Delimitation & Redaction Guardrails:**
   - User complaint inputs are strictly delimited as untrusted data (`Complaint text: """{text}"""`) within the system prompt to mitigate prompt injection and indirect instruction leakage.

4. **Public Cloud Provider Evaluation:**
   - In environments configured with hosted LLMs (`TRIAGE_PROVIDER=llm`), operations teams must ensure the API agreement guarantees a zero-data-retention (ZDR) policy. Where ZDR is unavailable, deployment must default to `OllamaTriage` or heuristic `RuleBasedTriage`.

## Justification & Tradeoffs
- **Compliance:** Decoupling citizen identity from triage prompts ensures compliance with data protection principles while still providing the LLM necessary spatial and descriptive context to triage hazards (such as contaminated water or live electrical wires).
- **Flexibility:** Organizations can switch between high-throughput hosted inference (Groq) and completely air-gapped zero-PII leakage (Ollama) simply by modifying environment variables without modifying source code.
