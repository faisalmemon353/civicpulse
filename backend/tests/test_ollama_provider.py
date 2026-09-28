"""
test_ollama_provider.py
=======================
Tests for OllamaTriage provider and its integration with:
- The factory (get_active_provider)
- The complaint triage route (POST /api/complaints)
- The meta providers route (GET /api/meta/providers)
- The Redis text-hash cache
- Graceful fallback when unreachable or failing
"""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app import triage_log
from app.config import settings
from app.providers.triage.factory import get_active_provider
from app.providers.triage.ollama import OllamaTriage
from app.schemas import Category, Priority


@pytest.fixture(autouse=True)
def clear_caches_and_logs():
    get_active_provider.cache_clear()
    triage_log.clear()
    yield
    get_active_provider.cache_clear()
    triage_log.clear()


# ---------------------------------------------------------------------------
# Unit tests for OllamaTriage
# ---------------------------------------------------------------------------


def test_ollama_factory_instantiation():
    """Factory returns OllamaTriage when triage_provider is configured for ollama."""
    with patch.object(settings, "triage_provider", "ollama"):
        provider = get_active_provider()
        assert isinstance(provider, OllamaTriage)
        assert provider.name == "llm:ollama"

    get_active_provider.cache_clear()

    with patch.object(settings, "triage_provider", "llm:ollama"):
        provider = get_active_provider()
        assert isinstance(provider, OllamaTriage)
        assert provider.name == "llm:ollama"


def test_ollama_successful_chat_response():
    """OllamaTriage parses /api/chat valid JSON response correctly."""
    mock_payload = {
        "message": {
            "role": "assistant",
            "content": json.dumps(
                {
                    "category": "water",
                    "priority": "high",
                    "summary": "Water pipe broken on 5th street",
                    "confidence": 0.92,
                }
            ),
        },
        "done": True,
    }

    mock_resp = httpx.Response(
        status_code=200,
        json=mock_payload,
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    with patch.object(httpx.Client, "post", return_value=mock_resp):
        provider = OllamaTriage(host="http://localhost:11434", model="llama3.2:1b")
        result = provider.triage("Water pipe burst and water everywhere", "5th Street")

        assert result.category == Category.water
        assert result.priority == Priority.high
        assert result.summary == "Water pipe broken on 5th street"
        assert result.confidence == 0.92


def test_ollama_successful_generate_format_response():
    """OllamaTriage handles legacy or /api/generate response shape ('response' key)."""
    mock_payload = {
        "response": json.dumps(
            {
                "category": "electricity",
                "priority": "normal",
                "summary": "Transformer spark reported",
                "confidence": 0.88,
            }
        ),
        "done": True,
    }

    mock_resp = httpx.Response(
        status_code=200,
        json=mock_payload,
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    with patch.object(httpx.Client, "post", return_value=mock_resp):
        provider = OllamaTriage()
        result = provider.triage("Transformer spark reported", "Sector 4")

        assert result.category == Category.electricity
        assert result.priority == Priority.normal
        assert result.confidence == 0.88


def test_ollama_retries_on_500_server_error_then_succeeds():
    """OllamaTriage retries on server 500 error and succeeds on second attempt."""
    error_resp = httpx.Response(
        status_code=500,
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )
    success_resp = httpx.Response(
        status_code=200,
        json={
            "message": {
                "content": json.dumps(
                    {
                        "category": "roads",
                        "priority": "low",
                        "summary": "Small pothole on side street",
                        "confidence": 0.75,
                    }
                )
            }
        },
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    with (
        patch.object(httpx.Client, "post", side_effect=[error_resp, success_resp]),
        patch("time.sleep"),
    ):  # skip sleep for speed
        provider = OllamaTriage()
        result = provider.triage("Small pothole on side street", "Lane B")

        assert result.category == Category.roads
        assert result.priority == Priority.low


def test_ollama_fails_fast_on_client_400():
    """Client error 400 is not retried and raises HTTPStatusError."""
    bad_request_resp = httpx.Response(
        status_code=400,
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    with patch.object(httpx.Client, "post", return_value=bad_request_resp):
        provider = OllamaTriage()
        with pytest.raises(httpx.HTTPStatusError):
            provider.triage("Test text", "Test Location")


def test_ollama_unreachable_triggers_runtime_error():
    """When Ollama is completely unreachable (connection refused/timeout), raises RuntimeError."""
    with (
        patch.object(httpx.Client, "post", side_effect=httpx.ConnectError("Connection refused")),
        patch("time.sleep"),
    ):
        provider = OllamaTriage()
        with pytest.raises(RuntimeError) as exc_info:
            provider.triage("Unreachable test", "Location")

        assert "OllamaTriage failed after retry" in str(exc_info.value)


def test_ollama_malformed_json_triggers_runtime_error():
    """When Ollama returns invalid JSON content after retries, raises RuntimeError."""
    mock_resp = httpx.Response(
        status_code=200,
        json={"message": {"content": "I am an AI and here is your classification: {broken json"}},
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    with patch.object(httpx.Client, "post", return_value=mock_resp), patch("time.sleep"):
        provider = OllamaTriage()
        with pytest.raises(RuntimeError):
            provider.triage("Malformed test", "Location")


def test_ollama_caches_result_in_redis():
    """Repeated calls with identical text hit Redis cache and avoid re-requesting Ollama."""
    mock_resp = httpx.Response(
        status_code=200,
        json={
            "message": {
                "content": json.dumps(
                    {
                        "category": "sanitation",
                        "priority": "normal",
                        "summary": "Garbage pile needs collection",
                        "confidence": 0.85,
                    }
                )
            }
        },
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # first call: cache miss

    with (
        patch.object(httpx.Client, "post", return_value=mock_resp) as mock_post,
        patch("app.providers.triage.ollama.get_redis_client", return_value=mock_redis),
    ):
        provider = OllamaTriage()

        res1 = provider.triage("Garbage pile needs collection", "Market")
        assert res1.category == Category.sanitation
        assert mock_post.call_count == 1
        assert mock_redis.set.call_count == 1

        # Second call: cache hit
        mock_redis.get.return_value = json.dumps(
            {
                "category": "sanitation",
                "priority": "normal",
                "summary": "Garbage pile needs collection",
                "confidence": 0.85,
            }
        ).encode("utf-8")

        res2 = provider.triage("Garbage pile needs collection", "Market")
        assert res2.category == Category.sanitation
        # post must NOT have been called again
        assert mock_post.call_count == 1


# ---------------------------------------------------------------------------
# Route integration tests (POST /api/complaints and GET /api/meta/providers)
# ---------------------------------------------------------------------------


def test_complaint_creation_with_healthy_ollama_provider(client, db_session):
    """POST /api/complaints succeeds with triaged_by == 'llm:ollama' when Ollama succeeds."""
    mock_resp = httpx.Response(
        status_code=200,
        json={
            "message": {
                "content": json.dumps(
                    {
                        "category": "streetlights",
                        "priority": "low",
                        "summary": "Streetlight pole flickering outside house",
                        "confidence": 0.9,
                    }
                )
            }
        },
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    ollama_provider = OllamaTriage()
    with (
        patch.object(httpx.Client, "post", return_value=mock_resp),
        patch("app.routes.complaints.get_active_provider", return_value=ollama_provider),
    ):
        response = client.post(
            "/api/complaints",
            json={
                "text": "Streetlight pole flickering outside house",
                "location": "North Avenue",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["triaged_by"] == "llm:ollama"
    assert body["category"] == "streetlights"
    assert body["priority"] == "low"
    assert body["triage_latency_ms"] >= 0


def test_complaint_creation_with_unreachable_ollama_falls_back_to_rules(client, db_session):
    """
    When Ollama service is down/unreachable, POST /api/complaints MUST NOT fail;
    it must gracefully fall back to rule-based triage (rules:fallback) and return 201.
    """
    ollama_provider = OllamaTriage()
    with (
        patch.object(httpx.Client, "post", side_effect=httpx.ConnectError("Connection refused")),
        patch("app.routes.complaints.get_active_provider", return_value=ollama_provider),
        patch("time.sleep"),
    ):
        response = client.post(
            "/api/complaints",
            json={
                "text": "Water pipeline burst creating flood on road",
                "location": "Central Square",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["triaged_by"] == "rules:fallback"
    assert body["category"] in ["water", "roads"]


def test_meta_providers_shows_ollama_active(client, db_session):
    """GET /api/meta/providers reflects 'llm:ollama' when active."""
    ollama_provider = OllamaTriage()
    with patch("app.routes.meta.get_active_provider", return_value=ollama_provider):
        response = client.get("/api/meta/providers")

    assert response.status_code == 200
    body = response.json()
    assert body["active_provider"] == "llm:ollama"
