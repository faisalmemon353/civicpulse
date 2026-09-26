"""
Redis client and connection management for CivicPulse.
"""
from typing import Optional
import redis

from app.config import settings

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
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
    except Exception:
        return None


def set_redis_client(client: Optional[redis.Redis]) -> None:
    """Explicitly sets or overrides the Redis client (useful in tests)."""
    global _redis_client
    _redis_client = client


def close_redis() -> None:
    """Closes and resets the Redis client."""
    global _redis_client
    if _redis_client is not None:
        try:
            _redis_client.close()
        except Exception:
            pass
        _redis_client = None
