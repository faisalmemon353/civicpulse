# CivicPulse Operations Runbook

Standard Operating Procedures (SOP) for deployment, rollback, observability, and incident recovery.

---

## 1. Quickstart & Deployment

### Local Development (Docker Compose)
To launch the complete 5-container architecture on a developer laptop:
```bash
# 1. Clone repository and initialize environment variables
cp .env.example .env

# 2. Launch development environment (hot-reload enabled)
docker compose up -d

# 3. Seed initial database with realistic complaints (idempotent)
docker compose exec backend python scripts/seed.py
```
Frontend is available at `http://localhost:8080`, Backend at `http://localhost:8000`.

### Production Deployment (Docker Compose)
```bash
# Build and run immutable production stack
docker compose -f compose.prod.yaml up -d --build
```

### Kubernetes Deployment
```bash
# Apply kustomize production overlay
kubectl apply -k k8s/overlays/prod

# Verify pod status and rollout
kubectl get pods -n civicpulse -w
```

---

## 2. Reading Logs & Observability

### Container Logs
CivicPulse outputs structured JSON logs to `stdout`. Every log line includes an `X-Request-ID` correlation ID.

- **Follow all logs:**
  ```bash
  docker compose logs -f
  ```
- **Inspect backend triage fallback events:**
  ```bash
  docker compose logs backend | grep -i "fallback"
  ```
- **Kubernetes pod logs:**
  ```bash
  kubectl logs -n civicpulse -l app=backend --tail=100 -f
  ```

### Inspecting Metrics & Triage Providers
- **Provider Status & Latency:**
  ```bash
  curl -s http://localhost:8000/api/meta/providers | jq .
  ```
- **Prometheus Metrics:**
  ```bash
  curl -s http://localhost:8000/metrics
  ```
- **Readiness Probe Check:**
  ```bash
  curl -s http://localhost:8000/ready
  ```

---

## 3. Rollback Procedures

### Kubernetes Rollback
1. **Immediate Imperative Rollback (Fastest - 3 a.m. incident response):**
   ```bash
   kubectl rollout undo deployment/backend -n civicpulse
   ```
   Verifies rollout progression:
   ```bash
   kubectl rollout status deployment/backend -n civicpulse
   ```

2. **Declarative GitOps Rollback (Auditable / Post-incident):**
   Revert the image SHA in `k8s/overlays/prod/kustomization.yaml` to the last known healthy commit SHA, commit to git, and re-apply:
   ```bash
   git revert HEAD
   git push origin main
   kubectl apply -k k8s/overlays/prod
   ```

### Docker Compose Rollback
```bash
# Revert to previous image tag or commit
IMAGE_TAG=<PREVIOUS_SHA> docker compose -f compose.prod.yaml up -d
```

---

## 4. Incident Response: Triage Provider Failures

### Scenario A: Triage Provider Times Out or Rate Limits (429)
- **Symptoms:** Logs contain `WARNING: Triage fallback event: primary provider 'llm:openrouter' failed`.
- **System Behavior:** Automatic degradation to `RuleBasedTriage` (`triaged_by: "rules:fallback"`). Citizen submissions are never lost.
- **Recovery Action:**
  1. Inspect provider quota or latency:
     ```bash
     curl http://localhost:8000/api/meta/providers
     ```
  2. Switch to offline Ollama provider instantly:
     ```bash
     export TRIAGE_PROVIDER=ollama
     docker compose up -d --no-deps backend
     ```

### Scenario B: Ollama Container Out of Memory or Unhealthy
- **Symptoms:** `GET /ready` returns 503 or Ollama restarts in an OOM loop.
- **Recovery Action:**
  1. Check model status inside container:
     ```bash
     docker exec civicpulse-ollama ollama list
     ```
  2. If missing, connect Ollama to edge network temporarily and pull weights:
     ```bash
     docker network connect civicpulse_edge civicpulse-ollama
     docker exec civicpulse-ollama ollama pull llama3.2:1b
     docker network disconnect civicpulse_edge civicpulse-ollama
     ```

### Scenario C: Redis Cache or Rate Limiter Unreachable
- **Symptoms:** `GET /ready` returns `{"status":"not_ready","dependencies":{"redis":"unreachable"}}`.
- **Recovery Action:**
  1. Restart Redis container:
     ```bash
     docker compose restart redis
     ```
  2. Verify AOF persistence log:
     ```bash
     docker compose logs redis
     ```
