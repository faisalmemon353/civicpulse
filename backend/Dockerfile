# ==============================================================================
# Multi-stage Dockerfile for CivicPulse FastAPI Backend
# ==============================================================================

# ---- Builder stage ----
FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f AS builder
WORKDIR /app

# Cache-friendly COPY order: install dependencies before copying full source
COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

# Copy source code and install the package itself without re-fetching dependencies
COPY . .
RUN pip install --no-cache-dir --prefix=/install --no-deps .

# ---- Runtime stage ----
FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f
WORKDIR /app

# Patch OS packages and create non-root user
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/* && \
    groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -m appuser

# Copy installed Python packages and application code from builder
COPY --from=builder /install /usr/local
COPY --from=builder /app /app

USER appuser
EXPOSE 8000

# Python-based healthcheck (no curl/wget needed)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

# Exec-form CMD to run FastAPI via uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
