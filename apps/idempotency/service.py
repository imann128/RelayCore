"""
Idempotency service — atomic Redis SET NX deduplication.

Design decision:
  We use a single atomic SET NX operation instead of a GET then SET pair.
  The GET/SET pattern has a race condition: two concurrent requests with the
  same key can both pass the GET check and both get processed.
  SET NX is atomic at the Redis level — only one caller wins.

Delivery guarantee:
  At-least-once delivery. If a worker crashes after SET NX but before
  persisting the delivery row, the event will not be retried (the key
  is already in Redis). This is the industry-standard tradeoff for systems
  that cannot coordinate two-phase commits across Redis and Postgres.
  Document this in your README — do not claim exactly-once.
"""

import hashlib
import redis
from django.conf import settings

_redis_client = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def generate_idempotency_key(source_name: str, delivery_header: str, payload: bytes) -> str:
    if delivery_header:
        return f"{source_name}:delivery:{delivery_header}"
    payload_hash = hashlib.sha256(payload).hexdigest()
    return f"{source_name}:payload:{payload_hash}"


def is_duplicate(idempotency_key: str, ttl_hours: int = 24) -> bool:
    """
    Atomic check-and-set using Redis SET NX EX.
    Returns True if this key was already seen (duplicate).
    Returns False if this is a new event (and registers it).
    """
    r = _get_redis()
    was_set = r.set(idempotency_key, 1, ex=ttl_hours * 3600, nx=True)
    return not was_set