# syntax=docker/dockerfile:1

# ---- Builder stage ----
FROM python:3.12-slim AS builder
WORKDIR /app

# Install dependencies from pyproject.toml
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy source code
COPY . .

# ---- Runtime stage ----
FROM python:3.12-slim
WORKDIR /app

# Create non‑root user
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/* && \
    groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -m appuser

# Copy built app from builder
COPY --from=builder /app /app

USER appuser
EXPOSE 8000

# Python‑based healthcheck (no curl)
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Exec‑form CMD to run FastAPI via uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
