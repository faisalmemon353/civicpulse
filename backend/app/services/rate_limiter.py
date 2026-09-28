"""
Distributed Redis-backed token bucket rate limiter for CivicPulse.
"""
import logging
import time

from fastapi import HTTPException, Request, status

from app.cache import get_redis_client
from app.config import settings

logger = logging.getLogger(__name__)

TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])

local data = redis.call("HMGET", key, "tokens", "last_updated")
local tokens = tonumber(data[1])
local last_updated = tonumber(data[2])

if tokens == nil then
    tokens = capacity - 1
    last_updated = now
    redis.call("HSET", key, "tokens", tokens, "last_updated", last_updated)
    redis.call("EXPIRE", key, ttl)
    return {1, 0}
else
    local elapsed = math.max(0, now - last_updated)
    tokens = math.min(capacity, tokens + elapsed * refill_rate)
    last_updated = now
    if tokens >= 1 then
        tokens = tokens - 1
        redis.call("HSET", key, "tokens", tokens, "last_updated", last_updated)
        redis.call("EXPIRE", key, ttl)
        return {1, 0}
    else
        redis.call("HSET", key, "tokens", tokens, "last_updated", last_updated)
        redis.call("EXPIRE", key, ttl)
        local needed = math.ceil((1 - tokens) / refill_rate)
        if needed < 1 then needed = 1 end
        return {0, needed}
    end
end
"""


def get_client_ip(request: Request) -> str:
    """Extracts client IP from request, taking into account X-Forwarded-For."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def check_rate_limit(request: Request) -> None:
    """
    Enforces token-bucket rate limiting based on client IP.
    Raises HTTPException(429) with Retry-After header if limit exceeded.
    """
    client = get_redis_client()
    if not client:
        # Graceful degradation if Redis is down
        return

    ip = get_client_ip(request)
    key = f"rate_limit:{ip}"
    capacity = settings.rate_limit_requests
    window = settings.rate_limit_window_seconds
    refill_rate = capacity / window
    now = time.time()
    ttl = max(window * 2, 60)

    try:
        res = client.eval(TOKEN_BUCKET_LUA, 1, key, capacity, refill_rate, now, ttl)
        allowed, retry_after = int(res[0]), int(res[1])
        if allowed != 1:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )
    except HTTPException:
        raise
    except Exception as exc:
        # If Redis errors (e.g. connection timeout), fail open to avoid service denial
        logger.debug("Rate limiter Redis error (failing open): %s", exc)
