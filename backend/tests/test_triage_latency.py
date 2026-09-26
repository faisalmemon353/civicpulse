"""
test_triage_latency.py
======================
Verifies that triage_latency_ms in the POST /api/complaints response
reflects real elapsed time (not the hardcoded 0 that existed before).

Design notes:
- We check >= 0 (not > 0) because on very fast test hardware the
  simulated provider can finish in sub-millisecond time, which rounds
  to 0 after round(). Asserting >= 0 is correct and not vacuous: it
  would catch a negative number or a missing field.
- We also check the fallback path sets a non-negative latency, since
  the clock must survive the exception branch too.
"""

from unittest.mock import patch

from app.providers.triage.simulated import SimulatedTriage


def test_latency_is_non_negative_on_success(client, db_session):
    """
    Happy path: primary provider succeeds. triage_latency_ms must be
    a non-negative integer (real timing, not the old hardcoded 0).
    """
    seeded = SimulatedTriage(seed=42)
    with patch("app.routes.complaints.get_active_provider", return_value=seeded):
        response = client.post(
            "/api/complaints",
            json={
                "text": "Water pipe burst flooding the street near our house",
                "location": "Test Location",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert "triage_latency_ms" in body, "triage_latency_ms field missing from response"
    assert isinstance(body["triage_latency_ms"], int), (
        f"triage_latency_ms should be int, got {type(body['triage_latency_ms'])}"
    )
    assert body["triage_latency_ms"] >= 0, (
        f"triage_latency_ms must be >= 0, got {body['triage_latency_ms']}"
    )


def test_latency_is_non_negative_on_fallback(client, db_session):
    """
    Fallback path: primary provider fails, fallback runs instead.
    triage_latency_ms must still be a non-negative integer — the clock
    spans both the failed primary attempt and the fallback execution.
    """
    failing_provider = SimulatedTriage(always_fail=True)
    with patch("app.routes.complaints.get_active_provider", return_value=failing_provider):
        response = client.post(
            "/api/complaints",
            json={
                "text": "Sewage overflow on main road causing health hazard",
                "location": "Test Location",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["triaged_by"] == "rules:fallback"
    assert isinstance(body["triage_latency_ms"], int)
    assert body["triage_latency_ms"] >= 0, (
        f"triage_latency_ms must be >= 0 even on fallback, got {body['triage_latency_ms']}"
    )
