"""
Redis client and connection management for CivicPulse.
"""

import redis

from app.config import settings
from app.logging import logger

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis | None:
    """
    Returns a singleton Redis client connected to settings.redis_url.
    Returns None if connection fails, enabling graceful degradation.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
        client.ping()
        _redis_client = client
        return _redis_client
    except (redis.RedisError, OSError, TimeoutError) as exc:
        logger.warning("Redis connection failed: %s", exc)
        return None


def set_redis_client(client: redis.Redis | None) -> None:
    """Explicitly sets or overrides the Redis client (useful in tests)."""
    global _redis_client
    _redis_client = client


def close_redis() -> None:
    """Closes and resets the Redis client."""
    global _redis_client
    if _redis_client is not None:
        try:
            _redis_client.close()
        except (redis.RedisError, OSError) as exc:
            logger.warning("Error closing Redis client: %s", exc)
        _redis_client = None


def check_redis() -> bool:
    """Verifies Redis connection health with a PING."""
    client = get_redis_client()
    if not client:
        return False
    try:
        return bool(client.ping())
    except (redis.RedisError, OSError, TimeoutError) as exc:
        logger.warning("Redis health check failed: %s", exc)
        return False