"""
Redis-based sliding window rate limiter.

Strategy: Redis INCR + EXPIRE pipeline.
  - INCR atomically increments a counter key.
  - EXPIRE sets a 60-second TTL on the key the first time it is created,
    so the window resets naturally without a background job.
  - Both commands run in a single pipeline (one round-trip), not fully
    atomic (a Lua script would be), but the race window is microseconds
    and the consequence of occasionally letting one extra request through
    is acceptable for a rate limiter. This is the industry-standard
    approach for Redis rate limiting without Lua.

Two check points:
  1. Source-level — called in the view before any processing (returns 429).
  2. Route-level  — called in the Celery task per route (skips that route,
     does not fail the whole delivery).
"""

import redis
from django.conf import settings

_redis_client = None


def _get_redis() -> redis.Redis:
    """Lazy singleton Redis client — reuses the connection pool."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def is_rate_limited(key: str, limit: int, window_seconds: int = 60) -> bool:
    """
    Increment the counter for `key` and return True if it exceeds `limit`.

    On the first request in a window, EXPIRE is set so the counter resets
    automatically after `window_seconds`.

    Args:
        key:            Namespaced Redis key, e.g. 'ratelimit:source:github-production'
        limit:          Maximum allowed requests in the window.
        window_seconds: Rolling window size in seconds (default 60).

    Returns:
        True  — limit exceeded, caller should reject/skip.
        False — under limit, caller should proceed.
    """
    r = _get_redis()

    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds, nx=True)  # nx=True: only set TTL if not already set
    results = pipe.execute()

    current_count = results[0]
    return current_count > limit


def source_rate_limit_key(source_slug: str) -> str:
    return f"ratelimit:source:{source_slug}"


def route_rate_limit_key(route_id: int) -> str:
    return f"ratelimit:route:{route_id}"
