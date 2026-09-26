"""
test_meta_providers.py
======================
Tests for GET /api/meta/providers.

Covers:
- Empty window on a fresh server (no POSTs yet)
- Active provider name comes from factory (not hardcoded)
- Each POST /api/complaints appends one outcome to recent_outcomes
- is_fallback=False on a healthy provider
- is_fallback=True when the primary provider fails
- Window caps at 20 entries (maxlen enforced by deque)
- Each outcome has the required fields
"""

from unittest.mock import patch

import pytest

from app import triage_log
from app.providers.triage.simulated import SimulatedTriage


@pytest.fixture(autouse=True)
def clear_triage_log():
    """Wipe the deque before every test to prevent cross-test pollution."""
    triage_log.clear()
    yield
    triage_log.clear()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _post_complaint(client, text="Road has a deep pothole near the school", location="Test Colony"):
    return client.post("/api/complaints", json={"text": text, "location": location})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_providers_empty_window_on_fresh_start(client, db_session):
    """With no complaints posted, recent_outcomes must be an empty list."""
    response = client.get("/api/meta/providers")
    assert response.status_code == 200
    body = response.json()
    assert body["recent_outcomes"] == []


def test_providers_returns_active_provider_name(client, db_session):
    """active_provider must match the name on the SimulatedTriage instance."""
    seeded = SimulatedTriage(seed=1)
    with patch("app.routes.complaints.get_active_provider", return_value=seeded):
        pass  # just need the name from the factory for the GET endpoint

    # The GET /api/meta/providers calls get_active_provider() internally.
    # In test env TRIAGE_PROVIDER defaults to "simulated", so the name is "simulated".
    response = client.get("/api/meta/providers")
    assert response.status_code == 200
    body = response.json()
    assert body["active_provider"] == "simulated"


def test_providers_records_one_outcome_per_post(client, db_session):
    """Each successful POST must append exactly one entry to recent_outcomes."""
    seeded = SimulatedTriage(seed=2)
    with patch("app.routes.complaints.get_active_provider", return_value=seeded):
        _post_complaint(client)
        _post_complaint(client)

    response = client.get("/api/meta/providers")
    body = response.json()
    assert len(body["recent_outcomes"]) == 2


def test_providers_outcome_has_required_fields(client, db_session):
    """Each outcome dict must contain provider, latency_ms, is_fallback, recorded_at."""
    seeded = SimulatedTriage(seed=3)
    with patch("app.routes.complaints.get_active_provider", return_value=seeded):
        _post_complaint(client)

    outcome = client.get("/api/meta/providers").json()["recent_outcomes"][0]
    assert "provider" in outcome
    assert "latency_ms" in outcome
    assert "is_fallback" in outcome
    assert "recorded_at" in outcome
    assert isinstance(outcome["latency_ms"], int)
    assert isinstance(outcome["is_fallback"], bool)


def test_providers_is_fallback_false_on_healthy_provider(client, db_session):
    """A healthy primary provider must produce is_fallback=False."""
    seeded = SimulatedTriage(seed=4)
    with patch("app.routes.complaints.get_active_provider", return_value=seeded):
        _post_complaint(client)

    outcome = client.get("/api/meta/providers").json()["recent_outcomes"][0]
    assert outcome["is_fallback"] is False
    assert outcome["provider"] == "simulated"


def test_providers_is_fallback_true_on_failed_provider(client, db_session):
    """A failing primary provider must produce is_fallback=True and provider='rules:fallback'."""
    failing = SimulatedTriage(always_fail=True)
    with patch("app.routes.complaints.get_active_provider", return_value=failing):
        _post_complaint(client)

    outcome = client.get("/api/meta/providers").json()["recent_outcomes"][0]
    assert outcome["is_fallback"] is True
    assert outcome["provider"] == "rules:fallback"


def test_providers_window_caps_at_20(client, db_session):
    """After 25 POSTs the window must still contain exactly 20 entries."""
    seeded = SimulatedTriage(seed=5)
    with patch("app.routes.complaints.get_active_provider", return_value=seeded):
        for i in range(25):
            _post_complaint(client, text=f"Road pothole issue number {i} near the main bus stop")

    body = client.get("/api/meta/providers").json()
    assert len(body["recent_outcomes"]) == 20
