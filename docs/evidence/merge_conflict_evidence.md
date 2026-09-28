# Merge Conflict Resolution Evidence (§4.A — 3 Marks)

## Context
During feature development of Docker Compose networking and container hardening, a deliberate merge conflict occurred on real code between branch `feature/docker-compose` and `dev` on the file `docker-compose.yml` (and subsequent migration to `compose.yaml`).

## Conflict Markers
```yaml
<<<<<<< HEAD (dev)
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: civicpulse
      POSTGRES_HOST_AUTH_METHOD=trust # dev only
=======
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-civicpulse}
>>>>>>> feature/docker-compose
```

## Resolution & Justification
- **Winning Version:** The version from `feature/docker-compose` utilizing parameterized environment variables (`${POSTGRES_USER:-postgres}`) and removing the insecure `POSTGRES_HOST_AUTH_METHOD=trust` was selected.
- **Why this version won:** Parameterizing credentials via environment variables prevents hardcoding secrets into Git history (avoiding the -20 deduction in §5.3) and adheres strictly to the 12-factor configuration guidelines and the Compose requirements in §3.2.

## Commit Evidence
- **Conflict Resolution Commit:** `62740c4` (`chore: resolve docker-compose conflict, apply review suggestions; add backend Dockerfile & .dockerignore`)
- **Resolved By:** Hassan Zahid & Faisal Memon
- **Pull Request:** Merged in PR #24.
