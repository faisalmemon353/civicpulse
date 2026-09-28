# AI Usage Attribution & Methodology (§5.5)

In compliance with course policy §5.5, this document details the AI tools and assistant interactions used during the development of CivicPulse.

---

## 1. Tools Employed
- **Google Antigravity IDE (Gemini Models):** Primary agentic pair-programming assistant used for code generation, test authoring, Docker architecture configuration, and system debugging.
- **Ollama (`llama3.2:1b`):** Self-hosted 1-billion parameter language model used as the runtime offline AI triage engine within the containerized Compose stack.

---

## 2. Components Shaped by AI

| Component | AI Role | Human / Developer Changes & Defense |
| :--- | :--- | :--- |
| **Backend Layer** | Drafted FastAPI routing, Pydantic schemas, and state machine transitions. | Validated strict 4-layer separation (no database queries inside routes). Enforced explicit transition matrix in `status_machine.py`. |
| **AI Triage Layer** | Generated protocol contracts, Ollama HTTP client, retry loops, and prompt injection tests. | Tuned Ollama timeout to 30.0s for CPU execution in Docker, enforced SHA-256 Redis content-hash caching, and added fallback warning logging. |
| **Frontend UI** | Scaffolding for React + Vite TypeScript pages and CSS styling. | Ensured `X-Cache` hit/miss header rendering, sanitized PII, and implemented relative `/api/` routing for Nginx proxy compatibility. |
| **DevOps & Containers** | Drafted multi-stage Dockerfiles and Docker Compose network segmentation. | Configured `internal: true` network isolation, pinned all base images with SHA256 digests, and diagnosed Ollama network egress resolution. |
| **Kubernetes Manifests** | Generated base manifests (Deployments, StatefulSets, Services, Ingress, HPA, VPA, PDB). | Verified `volumeClaimTemplates` for PostgreSQL, configured HPA scaleUp/scaleDown windows, and set VPA in recommend-only mode (`updateMode: "Off"`). |

---

## 3. Engineering Justification & Viva Readiness
All architectural decisions, line-level code changes, and failure modes have been audited, defended, and documented across `docs/ENGINEERING-NOTES.md` and the four Architecture Decision Records (ADRs).
