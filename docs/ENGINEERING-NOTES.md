# CivicPulse Engineering Notes (§5.2)

Comprehensive analysis and operational reflections addressing the core architecture decisions and failure modes.

---

### 1. Three things that differ between your laptop and a CI runner, and the exact lines that freeze each

1. **Python and Node Runtime Environments (Minor versions, system libraries, and C extensions):**
   - *Problem:* Local machines often run slightly different Python or Node patch versions, system glibc variants, or pip caches compared to GitHub Actions Ubuntu runners.
   - *Freezing Line:* In [`backend/Dockerfile`](file:///c:/Users/AS/OneDrive/Desktop/scd/civicpulse/backend/Dockerfile#L7-L17), both builder and runtime base images are pinned by exact digest:
     ```dockerfile
     FROM python:3.12-slim@sha256:d188aa7d97607730e6689b9d799d50041d8b67b66df2bfb15db3b9ff0ca84ee9
     ```
     Similarly, [`frontend/Dockerfile`](file:///c:/Users/AS/OneDrive/Desktop/scd/civicpulse/frontend/Dockerfile#L7-L21) pins `node:22-alpine` and `nginx:1.27-alpine` by immutable SHA256 digest.

2. **Filesystem User Permissions and Host UID/GID Mapping:**
   - *Problem:* Local developers run Docker rootless or as arbitrary user IDs, whereas CI runners run as default root Docker daemons, leading to permissions discrepancies on mounted files and sockets.
   - *Freezing Line:* In [`backend/Dockerfile`](file:///c:/Users/AS/OneDrive/Desktop/scd/civicpulse/backend/Dockerfile#L37-L38):
     ```dockerfile
     USER appuser
     ```
     Enforces execution under an unprivileged `appuser` (UID 10001) across all environments.

3. **Compute Constraints and Resource Allocation:**
   - *Problem:* A laptop with 16 GB RAM and 8 CPU cores behaves differently from a constrained 2-core / 7 GB GitHub Actions runner during concurrent load.
   - *Freezing Line:* In [`compose.yaml`](file:///c:/Users/AS/OneDrive/Desktop/scd/civicpulse/compose.yaml#L30-L36) and [`k8s/base/backend.yaml`](file:///c:/Users/AS/OneDrive/Desktop/scd/civicpulse/k8s/base/backend.yaml#L45-L53), CPU and memory are strictly bounded:
     ```yaml
     resources:
       requests:
         cpu: "100m"
         memory: "128Mi"
       limits:
         cpu: "500m"
         memory: "512Mi"
     ```

---

### 2. Where your pipeline sits on the CI/CD maturity ladder (Lecture 03, Slide 32)

- **Current Rung: Rung 3 (Automated Continuous Integration and Continuous Deployment with Artifact Gating).**
  - *Justification:* On pull requests, the pipeline executes static analysis (`ruff`, `mypy`, `eslint`, `tsc`), runs unit and integration tests with code coverage gating ($\ge 65\%$), performs vulnerability scans (`trivy`), validates manifests (`kubeconform`), and runs end-to-end container integration tests. On merge to `main`, immutable container images are built, tagged by commit SHA, signed, and deployed to an ephemeral Kubernetes cluster with ingress smoke tests.
- **Next Rung: Rung 4 (GitOps Continuous Delivery with Automated Canary Rollouts and Observability Feedback).**
  - *What it buys:* Shifts deployment control to an in-cluster reconciler (e.g., Argo CD / Flux). Instead of CI pushing directly into the cluster via `kubectl apply`, Git acts as the single declarative source of truth. Automated progressive traffic splitting (e.g., Argo Rollouts with Prometheus metrics) automatically rolls back deployments if error rates exceed 0.1%, eliminating all human deployment risk.

---

### 3. The exact line guaranteeing build-once-deploy-many, and what breaks without it

- **The Guaranteeing Line:** [`frontend/nginx.conf`](file:///c:/Users/AS/OneDrive/Desktop/scd/civicpulse/frontend/nginx.conf#L14-L16):
  ```nginx
  location /api/ {
      proxy_pass http://backend:8000;
  }
  ```
- **What breaks without it:**
  In Single Page Applications, building frontend bundles with client-side environment variables (`import.meta.env.VITE_API_URL`) bakes static URL strings (e.g. `http://localhost:8000`) into the transpiled JavaScript files. Without the relative Nginx reverse-proxy approach, a container image built for local development cannot run in staging or Kubernetes without re-running `npm run build`, permanently violating the immutable container artifact rule.

---

### 4. Correctness in a probabilistic LLM component & maintaining deterministic CI (Lecture 01, Slide 34)

- **Definition of "Correct":**
  Because natural language models are stochastic, "correctness" cannot mean identical character-for-character responses. Instead, correctness is bounded by contract:
  1. **Schema Integrity:** The payload strictly conforms to the `TriageResult` Pydantic model (`category` in valid enum, `priority` in valid enum, `summary` $\le 140$ chars).
  2. **Bounded Execution:** Total round-trip latency does not violate the SLA (10s timeout cap + single jittered retry).
  3. **Guaranteed Availability:** In case of model failure, the service gracefully degrades to `RuleBasedTriage` (`triaged_by = "rules:fallback"`), never returning HTTP 500.
- **Keeping CI Deterministic:**
  CI pipelines cannot depend on external LLM APIs (due to token limits, flakiness, or network drops). CI pins `TRIAGE_PROVIDER=simulated` ([`compose.yaml`](file:///c:/Users/AS/OneDrive/Desktop/scd/civicpulse/compose.yaml#L65)), activating `SimulatedTriage` with seeded pseudo-random engines. This delivers deterministic, instant test outcomes with zero flakiness.

---

### 5. HPA Lag: Timeline between offered load rising and replicas rising

- **Measured Lag:** Between 45 and 75 seconds from initial traffic surge to ready replica capacity.
- **Where the time goes:**
  1. *Metrics Scrape Interval (15s):* `metrics-server` samples pod CPU utilization every 15 seconds.
  2. *HPA Evaluation Period (15s):* The Kubernetes controller-manager evaluates HPA loops every 15 seconds.
  3. *Pod Scheduling & Image Pull (5–10s):* Kube-scheduler assigns pods to nodes; container runtimes verify images.
  4. *Container Startup & Health Probes (10–20s):* Startup probes poll `/health` every 2 seconds with a required initial success before the pod is marked `Ready` and added to the Service endpoint slice.
- **What reduces it:**
  - Lowering the `metrics-server` scrape interval to 5s.
  - Pre-pulling image layers on all worker nodes (daemonset / image caching).
  - Tuning the HPA stabilization window and setting `readinessProbe.periodSeconds` to 2s.

---

### 6. Why VPA runs in "Off" mode and the failure mode of running alongside HPA

- **Why VPA is in "Off" mode:** [`k8s/base/vpa.yaml`](file:///c:/Users/AS/OneDrive/Desktop/scd/civicpulse/k8s/base/vpa.yaml#L10-L11):
  ```yaml
  updatePolicy:
    updateMode: "Off"
  ```
  VPA operates strictly in recommendation mode, calculating target CPU/memory baselines without evicting running pods.
- **The Failure Mode (Flapping / Destabilization Loop):**
  HPA scales horizontal pod count based on CPU utilization calculated as:
  $$\text{Utilization} = \frac{\text{Actual CPU Usage}}{\text{Requested CPU}}$$
  If VPA operates in `Auto` mode simultaneously:
  1. Incoming traffic increases CPU usage.
  2. HPA schedules additional pods. Concurrently, VPA observes high usage and increases the pod's `resources.requests.cpu`.
  3. Increasing the denominator ($\text{requests.cpu}$) artificially lowers the computed utilization percentage below 60%.
  4. HPA observes the low utilization and scales pods down.
  5. Fewer pods now bear the load, driving per-pod usage higher, causing VPA to raise requests even further.
  The two controllers fight each other in an infinite cycle of pod evictions, flapping, and capacity degradation.

---

### 7. Internal Network Egress Isolation vs Hosted LLMs

- **The Tradeoff:**
  Section 3.2 enforces `internal: true` on the `civicpulse_internal` bridge network to ensure PostgreSQL and Redis are physically unreachable from the public internet. However, a hosted LLM provider (Groq / OpenRouter) requires external internet egress to make HTTPS calls.
- **How it is resolved:**
  The `backend` container is deliberately configured with dual network attachments:
  ```yaml
  networks:
    - edge      # Outbound internet access to reach external LLM endpoints and frontend
    - internal  # Isolated internal access to database and cache
  ```
  The database and cache remain strictly on `internal` only, with no route to the outside world.
  For air-gapped environments without any internet connectivity, `TRIAGE_PROVIDER=ollama` runs on `internal` using local weights stored in the persistent `ollama_models` volume.

---

### 8. The Failure That Cost More Than An Hour

- **Symptoms:**
  Submitting citizen complaints continuously resulted in `triaged_by: "simulated"` instead of invoking Ollama AI, and running `ollama pull llama3.2:1b` inside the container immediately exited with `dial tcp: lookup registry.ollama.ai on 127.0.0.11:53: server misbehaving`.
- **Initial False Belief:**
  We initially hypothesized that FastAPI's triage factory was buggy or that `compose.yaml` changes were not being mounted into the container filesystem.
- **The Revealing Commands & Truth:**
  1. Running `docker exec civicpulse-backend env` showed:
     ```text
     TRIAGE_PROVIDER=simulated
     ```
     revealing that Docker Compose does **not** dynamically reload environment variables on running containers without recreating the container (`docker compose up -d --no-deps backend`).
  2. Running `docker exec civicpulse-ollama ping registry.ollama.ai` confirmed total DNS and network failure because Ollama was joined to `internal: true` (which blocks all internet egress). Connecting Ollama temporarily to `edge` immediately unblocked model downloads and enabled full local AI triage.
