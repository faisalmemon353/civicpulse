"""
test_redis_cache.py
===================
Tests for Item 4: Redis Cache Layer:
1. GET /api/stats read-through caching with 30s TTL, X-Cache: HIT|MISS, and write invalidation.
2. Distributed token-bucket rate limiter on POST /api/complaints with 429 + Retry-After.
3. LLMTriage text-hash caching with 24h TTL by SHA256 of complaint text.
"""
import hashlib
import json
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.cache import get_redis_client
from app.config import settings
from app.providers.triage.base import TriageResult
from app.providers.triage.llm import LLMTriage
from app.routes.stats import STATS_CACHE_KEY, STATS_CACHE_TTL_SECONDS
from app.schemas import Category, Priority


# =====================================================================
# 1. Stats Caching Tests
# =====================================================================

def test_stats_cache_miss_then_hit(client, db_session):
    """
    On cold cache, GET /api/stats must return X-Cache: MISS and populate Redis.
    On immediate second call, it must return X-Cache: HIT with identical payload.
    """
    r1 = client.get("/api/stats")
    assert r1.status_code == 200
    assert r1.headers.get("X-Cache") == "MISS"
    data1 = r1.json()
    assert "by_category" in data1
    assert "by_priority" in data1
    assert "total" in data1

    # Verify key was written to Redis with positive TTL <= 30
    redis = get_redis_client()
    assert redis is not None
    ttl = redis.ttl(STATS_CACHE_KEY)
    assert 0 < ttl <= STATS_CACHE_TTL_SECONDS

    # Second call must be a HIT
    r2 = client.get("/api/stats")
    assert r2.status_code == 200
    assert r2.headers.get("X-Cache") == "HIT"
    assert r2.json() == data1


def test_stats_cache_invalidated_on_complaint_creation(client, db_session):
    """
    Creating a complaint via POST /api/complaints must invalidate stats cache,
    forcing the subsequent GET /api/stats to return X-Cache: MISS and updated counts.
    """
    # Prime cache
    r1 = client.get("/api/stats")
    assert r1.status_code == 200
    assert r1.headers.get("X-Cache") == "MISS"
    initial_total = r1.json()["total"]

    # Cache is now warm
    r2 = client.get("/api/stats")
    assert r2.headers.get("X-Cache") == "HIT"

    # POST a complaint
    post_res = client.post(
        "/api/complaints",
        json={
            "text": "Broken water pipeline overflowing onto the street",
            "location": "Sector G-9, Islamabad",
        },
    )
    assert post_res.status_code == 201

    # Cache must now be invalidated -> MISS, total increments by 1
    r3 = client.get("/api/stats")
    assert r3.status_code == 200
    assert r3.headers.get("X-Cache") == "MISS"
    assert r3.json()["total"] == initial_total + 1


def test_stats_cache_invalidated_on_status_update(client, db_session):
    """
    Updating complaint status via PATCH /api/complaints/{id}/status must
    invalidate stats cache so status aggregates stay fresh.
    """
    # Create a complaint
    post_res = client.post(
        "/api/complaints",
        json={
            "text": "Electricity pole sparked and wires fell down",
            "location": "Gulberg 3, Lahore",
        },
    )
    assert post_res.status_code == 201
    complaint_id = post_res.json()["id"]

    # Prime stats cache
    r1 = client.get("/api/stats")
    assert r1.headers.get("X-Cache") == "MISS"
    r2 = client.get("/api/stats")
    assert r2.headers.get("X-Cache") == "HIT"

    # Transition open -> in_progress
    patch_res = client.patch(
        f"/api/complaints/{complaint_id}/status",
        json={"status": "in_progress"},
    )
    assert patch_res.status_code == 200

    # Cache must be invalidated -> MISS
    r3 = client.get("/api/stats")
    assert r3.headers.get("X-Cache") == "MISS"


# =====================================================================
# 2. Distributed Rate Limiter Tests
# =====================================================================

def test_rate_limiter_blocks_excess_requests(client, db_session):
    """
    When rate limit capacity is reached, subsequent requests from the same IP
    must be rejected with HTTP 429 Too Many Requests and a Retry-After header.
    """
    with patch.object(settings, "rate_limit_requests", 3), \
         patch.object(settings, "rate_limit_window_seconds", 60):

        # First 3 requests succeed
        for i in range(3):
            res = client.post(
                "/api/complaints",
                json={"text": f"Complaint number {i+1} for streetlights", "location": "Test Area"},
                headers={"X-Forwarded-For": "192.168.1.100"},
            )
            assert res.status_code == 201

        # 4th request from same IP is rate limited
        blocked_res = client.post(
            "/api/complaints",
            json={"text": "Complaint number 4 should fail", "location": "Test Area"},
            headers={"X-Forwarded-For": "192.168.1.100"},
        )
        assert blocked_res.status_code == 429
        assert "Retry-After" in blocked_res.headers
        retry_after = int(blocked_res.headers["Retry-After"])
        assert retry_after > 0


def test_rate_limiter_isolated_by_client_ip(client, db_session):
    """
    Rate limits must be keyed per client IP: one IP hitting its limit
    must NOT block requests from a different client IP.
    """
    with patch.object(settings, "rate_limit_requests", 2), \
         patch.object(settings, "rate_limit_window_seconds", 60):

        # Exhaust IP A
        for _ in range(2):
            res = client.post(
                "/api/complaints",
                json={"text": "Pothole on main boulevard road", "location": "Test Area"},
                headers={"X-Forwarded-For": "10.0.0.1"},
            )
            assert res.status_code == 201

        # 3rd request from IP A is blocked
        res_a_blocked = client.post(
            "/api/complaints",
            json={"text": "Another pothole reported", "location": "Test Area"},
            headers={"X-Forwarded-For": "10.0.0.1"},
        )
        assert res_a_blocked.status_code == 429

        # Request from IP B must succeed
        res_b = client.post(
            "/api/complaints",
            json={"text": "Water leakage in sector 7", "location": "Test Area"},
            headers={"X-Forwarded-For": "10.0.0.2"},
        )
        assert res_b.status_code == 201


# =====================================================================
# 3. LLMTriage Text-Hash Cache Tests
# =====================================================================

def test_llm_triage_caches_result_by_text_hash():
    """
    LLMTriage must cache successful outcomes in Redis with 24h TTL,
    keyed by SHA256 of complaint text. Repeated triage with the same text
    must return the cached result without invoking the OpenAI client.
    """
    provider = LLMTriage()
    sample_text = "Severe sewage overflow outside the primary school gate"
    sample_location = "Block 4, Clifton, Karachi"
    text_hash = hashlib.sha256(sample_text.strip().encode("utf-8")).hexdigest()
    expected_cache_key = f"triage:llm:{text_hash}"

    # Mock OpenAI client chat completion
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps({
        "category": "sanitation",
        "priority": "high",
        "summary": "Sewage overflow outside school gate",
        "confidence": 0.95,
    })
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch.object(provider._client.chat.completions, "create", return_value=mock_response) as mock_create:
        # First call: cache miss -> invokes OpenAI client
        res1 = provider.triage(sample_text, sample_location)
        assert mock_create.call_count == 1
        assert res1.category == Category.sanitation
        assert res1.priority == Priority.high
        assert res1.confidence == 0.95

        # Verify cached in Redis with 24h TTL (86400s)
        redis = get_redis_client()
        assert redis is not None
        assert redis.exists(expected_cache_key)
        ttl = redis.ttl(expected_cache_key)
        assert 0 < ttl <= 86400

        # Second call with identical text: cache hit -> OpenAI client NOT called
        res2 = provider.triage(sample_text, sample_location)
        assert mock_create.call_count == 1  # Still 1, did not call again
        assert res2.category == Category.sanitation
        assert res2.priority == Priority.high
        assert res2.summary == res1.summary
        assert res2.confidence == res1.confidence


def test_llm_triage_does_not_cache_failures():
    """
    If the LLM call fails, no entry should be created in Redis,
    ensuring subsequent attempts can try again.
    """
    provider = LLMTriage()
    bad_text = "Some random text that triggers error"
    text_hash = hashlib.sha256(bad_text.strip().encode("utf-8")).hexdigest()
    cache_key = f"triage:llm:{text_hash}"

    with patch.object(provider._client.chat.completions, "create", side_effect=ValueError("Corrupt response")):
        with pytest.raises(RuntimeError):
            provider.triage(bad_text, "Test Location")

    redis = get_redis_client()
    assert redis is not None
    assert not redis.exists(cache_key)


# =====================================================================
# 4. Graceful Degradation (Redis Unavailable)
# =====================================================================

def test_stats_gracefully_handles_redis_down(client, db_session):
    """
    If Redis is down or unreachable, GET /api/stats must continue to function,
    falling back to querying the database directly with X-Cache: MISS.
    """
    with patch("app.routes.stats.get_redis_client", return_value=None):
        res = client.get("/api/stats")
        assert res.status_code == 200
        assert res.headers.get("X-Cache") == "MISS"
        assert "total" in res.json()


def test_rate_limiter_fails_open_if_redis_down(client, db_session):
    """
    If Redis is down, the rate limiter must fail open to avoid taking
    down municipal complaint reporting.
    """
    with patch("app.services.rate_limiter.get_redis_client", return_value=None):
        res = client.post(
            "/api/complaints",
            json={"text": "Water pipeline burst causing flood", "location": "Test Area"},
        )
        assert res.status_code == 201

