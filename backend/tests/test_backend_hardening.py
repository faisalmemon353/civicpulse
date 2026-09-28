"""
test_backend_hardening.py
=========================
Tests for Item 5: Backend Hardening:
1. Real /health (liveness probe, never touches DB)
2. Real /ready (readiness probe, checks Postgres & Redis, 503 with failed dependency name)
3. Real /metrics (Prometheus exposition format with counters & histograms)
4. Structured JSON logging with request_id propagation (X-Request-ID header)
5. Fallback event warning log (complaint_id, provider_name, error class/message)
6. HTTP 400 field-level validation error responses (replacing 422)
7. Lifespan graceful shutdown (connection pool disposal)
"""
import json
import logging
import uuid
from unittest.mock import patch

import pytest

from app.logging import JSONFormatter
from app.main import app, lifespan
from app.providers.triage.simulated import SimulatedTriage

# =====================================================================
# 1. Health & Readiness Probes
# =====================================================================

def test_health_probe_returns_ok_without_db(client):
    """
    GET /health is a liveness probe: must return 200 {"status": "ok"}
    and never query the database.
    """
    with patch("app.db.check_postgres") as mock_pg:
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}
        assert mock_pg.call_count == 0


def test_ready_probe_all_healthy(client, db_session):
    """
    GET /ready returns 200 {"status": "ready"} when Postgres and Redis are up.
    """
    with patch("app.routes.system.check_postgres", return_value=True), \
         patch("app.routes.system.check_redis", return_value=True):
        res = client.get("/ready")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "ready"
        assert body["checks"]["database"] is True
        assert body["checks"]["cache"] is True


def test_ready_probe_database_down_returns_503(client):
    """
    GET /ready returns 503 Service Unavailable naming 'database' when Postgres is down.
    """
    with patch("app.routes.system.check_postgres", return_value=False), \
         patch("app.routes.system.check_redis", return_value=True):
        res = client.get("/ready")
        assert res.status_code == 503
        body = res.json()
        assert body["status"] == "not ready"
        assert "database" in body["failed"]
        assert body["checks"]["database"] is False
        assert body["checks"]["cache"] is True


def test_ready_probe_cache_down_returns_503(client):
    """
    GET /ready returns 503 Service Unavailable naming 'cache' when Redis is down.
    """
    with patch("app.routes.system.check_postgres", return_value=True), \
         patch("app.routes.system.check_redis", return_value=False):
        res = client.get("/ready")
        assert res.status_code == 503
        body = res.json()
        assert body["status"] == "not ready"
        assert "cache" in body["failed"]
        assert body["checks"]["database"] is True
        assert body["checks"]["cache"] is False


def test_ready_probe_both_down_returns_503(client):
    """
    GET /ready returns 503 naming both dependencies when both are unreachable.
    """
    with patch("app.routes.system.check_postgres", return_value=False), \
         patch("app.routes.system.check_redis", return_value=False):
        res = client.get("/ready")
        assert res.status_code == 503
        body = res.json()
        assert body["status"] == "not ready"
        assert "database" in body["failed"]
        assert "cache" in body["failed"]


# =====================================================================
# 2. Prometheus Metrics
# =====================================================================

def test_metrics_endpoint_returns_prometheus_format(client):
    """
    GET /metrics returns text in standard Prometheus exposition format.
    """
    # Trigger an endpoint so HTTP metrics are recorded
    client.get("/health")

    res = client.get("/metrics")
    assert res.status_code == 200
    assert "text/plain" in res.headers.get("content-type", "")

    content = res.text
    assert "civicpulse_http_requests_total" in content
    assert "civicpulse_http_request_duration_seconds" in content
    assert "civicpulse_triage_duration_seconds" in content
    assert "civicpulse_triage_fallbacks_total" in content


# =====================================================================
# 3. Request-ID Propagation & Middleware
# =====================================================================

def test_request_id_propagated_from_client_header(client):
    """
    Incoming X-Request-ID header must be preserved on the response.
    """
    custom_id = "test-req-id-12345"
    res = client.get("/health", headers={"X-Request-ID": custom_id})
    assert res.status_code == 200
    assert res.headers.get("X-Request-ID") == custom_id


def test_request_id_generated_when_absent(client):
    """
    When X-Request-ID is absent from request, a valid UUID must be generated.
    """
    res = client.get("/health")
    assert res.status_code == 200
    generated_id = res.headers.get("X-Request-ID")
    assert generated_id is not None
    # Must be valid UUID
    uuid.UUID(generated_id)


# =====================================================================
# 4. Structured JSON Logging & Fallback Warning
# =====================================================================

def test_json_formatter_produces_valid_json():
    """
    JSONFormatter must format log records as parseable single-line JSON.
    """
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.WARNING,
        pathname="test.py",
        lineno=10,
        msg="Test warning message",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "WARNING"
    assert parsed["logger"] == "test_logger"
    assert parsed["message"] == "Test warning message"
    assert "timestamp" in parsed
    assert "request_id" in parsed


def test_fallback_event_emits_warning_log(client, db_session, caplog):
    """
    When primary triage provider raises, a WARNING log must be emitted
    containing complaint_id, provider_name, error_class, and error_message.
    """
    failing_provider = SimulatedTriage(always_fail=True)

    with (
        caplog.at_level(logging.WARNING, logger="civicpulse"),
        patch("app.routes.complaints.get_active_provider", return_value=failing_provider),
    ):
            res = client.post(
                "/api/complaints",
                json={
                    "text": "Water pipeline burst causing flood in main road",
                    "location": "Sector F-7, Islamabad",
                },
            )

    assert res.status_code == 201
    complaint_id = res.json()["id"]

    # Verify a WARNING record with fallback details exists
    fallback_records = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "fallback" in r.getMessage().lower()
    ]
    assert len(fallback_records) >= 1
    rec = fallback_records[0]
    assert getattr(rec, "complaint_id", "") == complaint_id
    assert getattr(rec, "provider_name", "") == "simulated"
    assert getattr(rec, "error_class", "") == "RuntimeError"


# =====================================================================
# 5. Field-Level 400 Validation Error Responses
# =====================================================================

def test_short_complaint_text_returns_400_with_field_errors(client, db_session):
    """
    Invalid request payload must return HTTP 400 Bad Request (not 422)
    with field-level error details.
    """
    # Text shorter than min_length=10
    res = client.post(
        "/api/complaints",
        json={"text": "short", "location": "Test Area"},
    )
    assert res.status_code == 400
    body = res.json()
    assert body["detail"] == "Validation error"
    assert "errors" in body
    fields = [err["field"] for err in body["errors"]]
    assert "text" in fields


def test_missing_location_returns_400_with_field_errors(client, db_session):
    """
    Missing required field must return HTTP 400 with location identified.
    """
    res = client.post(
        "/api/complaints",
        json={"text": "Water pipeline burst causing flood in street"},
    )
    assert res.status_code == 400
    body = res.json()
    assert body["detail"] == "Validation error"
    fields = [err["field"] for err in body["errors"]]
    assert "location" in fields


# =====================================================================
# 6. Lifespan Graceful Shutdown
# =====================================================================

@pytest.mark.anyio
async def test_lifespan_graceful_shutdown():
    """
    Lifespan context manager must cleanly startup and dispose resources on shutdown.
    """
    with patch("app.main.engine.dispose") as mock_dispose, \
         patch("app.main.close_redis") as mock_close_redis:
        async with lifespan(app):
            pass  # running
        # After exiting lifespan (SIGTERM / shutdown)
        assert mock_dispose.call_count == 1
        assert mock_close_redis.call_count == 1
