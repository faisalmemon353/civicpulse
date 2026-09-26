from unittest.mock import patch

from app.providers.triage.simulated import SimulatedTriage


def test_failing_provider_triggers_fallback(client, db_session):
    """
    The single most important test in the AI layer: if the active
    triage provider raises, POST /api/complaints must still succeed
    (201) by falling back to rule-based triage, and must record
    triaged_by == 'rules:fallback'.
    """
    failing_provider = SimulatedTriage(always_fail=True)

    with patch("app.routes.complaints.get_active_provider", return_value=failing_provider):
        response = client.post(
            "/api/complaints",
            json={
                "text": "Water pipe burst flooding the street near our house",
                "location": "Test Location",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["triaged_by"] == "rules:fallback"
    assert body["category"] in [
        "water", "electricity", "sanitation", "roads", "streetlights", "other"
    ]