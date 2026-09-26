"""
Prometheus metrics exposition for CivicPulse.
"""
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

# HTTP Request Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "civicpulse_http_requests_total",
    "Total HTTP requests handled by CivicPulse",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "civicpulse_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Triage Specific Metrics
TRIAGE_DURATION_SECONDS = Histogram(
    "civicpulse_triage_duration_seconds",
    "Time taken to triage a complaint in seconds",
    ["provider"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

TRIAGE_FALLBACKS_TOTAL = Counter(
    "civicpulse_triage_fallbacks_total",
    "Total number of times triage failed and fell back to rule-based triage",
    ["primary_provider"],
)


def record_triage_metrics(provider: str, latency_seconds: float, is_fallback: bool, primary_provider: str = "") -> None:
    """Records triage duration and fallback counts in Prometheus."""
    TRIAGE_DURATION_SECONDS.labels(provider=provider).observe(latency_seconds)
    if is_fallback:
        TRIAGE_FALLBACKS_TOTAL.labels(primary_provider=primary_provider or provider).inc()
