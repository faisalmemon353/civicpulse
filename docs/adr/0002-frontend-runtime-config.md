# ADR 0002: Frontend Runtime Configuration via Reverse Proxy

## Status
Accepted

## Context
A Single Page Application (SPA) built with Vite and React must communicate with the CivicPulse backend API across multiple deployment targets: local developer workstations, Docker Compose networks, Kubernetes clusters, and automated CI/CD environments. Hardcoding or baking the backend API URL into the client bundle at build time using `import.meta.env.VITE_*` violates 12-factor application principles, requiring different build artifacts for each deployment environment.

## Decision
We adopt the **Nginx Reverse Proxy** architecture for runtime configuration:
1. The frontend application strictly dispatches API calls to relative paths starting with `/api/` (e.g., `fetch('/api/complaints')`).
2. In local development, Vite's internal development server proxies `/api` requests to the local backend at `http://127.0.0.1:8000`.
3. In containerized environments (Docker Compose / production Nginx image), Nginx serves the static assets and reverse-proxies `/api/` traffic directly to the backend service upstream (`http://backend:8000/api/`).
4. In Kubernetes environments, the Ingress controller routes ingress paths (`/api` to the backend Service, and `/` to the frontend Service).

## Justification & Tradeoffs
By keeping API paths relative, the frontend build artifact (`dist/`) is completely environment-agnostic and truly immutable—the exact same container image can be promoted from test to staging to production without rebuilding. This approach completely eliminates Cross-Origin Resource Sharing (CORS) preflight overhead in production, prevents sensitive backend infrastructure topology from leaking into client-side bundles, and avoids brittle container startup entrypoint scripts that mutate static assets (such as generating dynamic `/config.js` files at runtime).
