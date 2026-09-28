# ADR 0003: Docker Compose Network Segmentation, Persistence Volumes, and Environment Isolation

## Status
Accepted

## Context
CivicPulse requires a robust containerization architecture covering both local developer workflows and production deployments. A production-ready microservice stack must address several critical operational concerns:
1. **Network Attack Surface**: Internet-facing components (Frontend / Nginx) must not have direct network access to critical datastores (PostgreSQL, Redis).
2. **External LLM Egress vs. Data Isolation**: Cloud LLM triage providers (Groq, OpenRouter, OpenAI) require public internet egress, while internal databases and caches must remain air-gapped from the public internet.
3. **Explicit State Persistence**: Container recreation must never result in loss of citizen complaints, LLM cache state, or re-downloading large neural network weights.
4. **Development Inner Loop vs. Production Immutability**: Developers need instant hot-reloading for rapid code iteration, whereas production environments require strict artifact immutability.

---

## Architectural Decisions

### 1. Dual-Network Segmentation (`edge` and `internal: true`)
We define two isolated Docker bridge networks:
```yaml
networks:
  edge:
    driver: bridge # Internet-facing frontend ↔ backend communication
  internal:
    driver: bridge
    internal: true # Air-gapped; no default gateway or route to the outside world
```

- **Frontend (`edge` only)**: Serves static assets and reverse-proxies `/api/` calls to `backend:8000`. It has **no route** to the internal network. Attempting `docker compose exec frontend ping database` fails with `ping: bad address 'database'`, guaranteeing that a compromised frontend cannot reach the database.
- **Backend (`edge` + `internal`)**: Bridges both networks as the single controlled gateway. It communicates with PostgreSQL and Redis on `internal`, while retaining outbound internet access through `edge` for cloud LLM triage providers (Groq, OpenRouter, OpenAI).
- **PostgreSQL & Redis (`internal` only)**: Live strictly on `internal: true`. They cannot establish outbound connections or receive inbound external connections. In production (`compose.prod.yaml`), no ports are published to the host.

#### Trade-off & Architectural Defense
Setting `internal: true` creates an intentional trade-off: containers on this network cannot reach the public internet. Therefore, any LLMTriage provider calling cloud APIs (e.g., Groq, OpenRouter) must run on a service attached to an external network (`backend` on `edge`). Conversely, local inference engines like **Ollama** can safely reside on `internal: true`, protected from the internet, as long as model weights are pre-mounted or persisted via volumes.

---

### 2. Justification for the Three Persistent Volumes

| Volume | Purpose & Storage Target | Justification |
|---|---|---|
| `pgdata` | Mounted to `/var/lib/postgresql/data` | **Durable Relational Persistence**: Stores all citizen complaint records, audit logs, and status transitions. Ensures transactional ACID durability across container restarts, image upgrades, and host reboots. |
| `redisdata` | Mounted to `/data` with `redis-server --appendonly yes` | **AOF Persistence**: Preserves cached LLM triage outcomes (24h TTL) and rate limit counters. Using Append-Only File (AOF) logging guarantees zero cache cold-starts and prevents burst traffic surges to LLM providers following a Redis restart. |
| `ollama_models` | Mounted to `/root/.ollama` | **Large Binary Asset Persistence**: Stores local LLM weights (e.g., `llama3.2:1b`, ~800MB–2GB). Without explicit volume persistence, every container restart would re-download the models over the network, introducing startup latency and network costs. |

---

### 3. Bind Mounts: Right in `compose.yaml`, Wrong in `compose.prod.yaml`

- **Why bind mounts (`./backend:/app`) are RIGHT in `compose.yaml`**:
  During local development, developer velocity depends on an immediate feedback loop. Mounting the host source code directory into `/app` alongside `uvicorn --reload` allows code edits to take effect instantly without rebuilding the container image or reinstalling dependencies.

- **Why bind mounts are WRONG in `compose.prod.yaml`**:
  1. **Artifact Immutability**: Production deployments must run the exact, tested, and scanned image artifact verified in the CI pipeline. Bind mounts bypass the container image and run whatever loose files exist on the host.
  2. **Security & Blast Radius**: Exposing the host filesystem to a container introduces path traversal risks and potential privilege escalation.
  3. **Portability & Orchestration**: Bind mounts bind the container to a specific directory structure on the host machine, breaking horizontal scaling, rolling updates, and multi-node orchestration (e.g., Kubernetes, Swarm).

---

### 4. Build Context & Multi-Stage Image Footprint

#### Context Size Optimization via `.dockerignore`
By excluding `.git`, `node_modules`, `.venv`, `__pycache__`, `tests`, and test fixtures:
- **Backend Context**: Reduced from 300MB+ (with local venv) to **~65 KB**.
- **Frontend Context**: Reduced from 250MB+ (with `node_modules` and `dist`) to **~280 KB**.

#### Multi-Stage Image Sizes
- **Backend**:
  - Builder stage (with gcc, wheel builds, dev tools): ~1.1 GB
  - Final runtime stage (`python:3.12-slim` + non-root `appuser:1001`): **~391 MB**
- **Frontend**:
  - Builder stage (`node:22-alpine` + `node_modules` + TypeScript): **~454 MB**
  - Final serve stage (`nginx:1.27-alpine` non-root with static HTML/JS/CSS only): **~93 MB** (all Node.js runtimes, npm caches, and TypeScript source files completely stripped).
