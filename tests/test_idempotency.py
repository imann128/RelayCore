"""
Tests for the idempotency service (Redis SET NX deduplication).

Key behaviours to verify:
  1. First call with a new key → not a duplicate, key is registered
  2. Second call with the same key → duplicate detected
  3. Different keys are independent
  4. Key generated from delivery header takes priority over hash
  5. Fallback key is derived from SHA-256 of raw bytes (not parsed JSON)

Note: the clear_cache autouse fixture in conftest.py flushes Redis before
each test so keys never bleed between tests.
"""

import hashlib
import json

import pytest

from apps.idempotency.service import generate_idempotency_key, is_duplicate


class TestIsDuplicate:
    """Tests for is_duplicate() — the atomic SET NX check."""

    def test_new_key_is_not_duplicate(self):
        assert is_duplicate('test:key:new') is False

    def test_same_key_second_call_is_duplicate(self):
        key = 'test:key:repeat'
        is_duplicate(key)          # first call: registers the key
        assert is_duplicate(key) is True

    def test_different_keys_are_independent(self):
        assert is_duplicate('test:key:alpha') is False
        assert is_duplicate('test:key:beta') is False
        # Both are new, neither should flag the other as duplicate
        assert is_duplicate('test:key:alpha') is True   # now it's a duplicate
        assert is_duplicate('test:key:beta') is True

    def test_returns_false_on_first_call_and_true_on_second(self):
        """Explicit assertion on return value sequence — documents the contract."""
        key = 'test:key:sequence'
        first  = is_duplicate(key)
        second = is_duplicate(key)
        third  = is_duplicate(key)

        assert first  is False   # new event
        assert second is True    # duplicate
        assert third  is True    # still a duplicate


class TestGenerateIdempotencyKey:
    """Tests for generate_idempotency_key() — key construction logic."""

    def test_delivery_header_takes_priority_over_body_hash(self):
        key = generate_idempotency_key(
            source_name='github',
            delivery_header='abc-123-uuid',
            payload=b'{"ref": "refs/heads/main"}',
        )
        assert key == 'github:delivery:abc-123-uuid'

    def test_empty_delivery_header_falls_back_to_sha256(self):
        body = b'{"ref": "refs/heads/main"}'
        expected_hash = hashlib.sha256(body).hexdigest()
        key = generate_idempotency_key(
            source_name='github',
            delivery_header='',
            payload=body,
        )
        assert key == f'github:payload:{expected_hash}'

    def test_key_uses_raw_bytes_not_parsed_json(self):
        """
        Two JSON strings that are semantically equal but have different key
        ordering must produce DIFFERENT hashes — we hash bytes, not parsed dicts.

        This is intentional: the hash is a content fingerprint of exactly what
        was received on the wire. If providers send the same payload with
        different key ordering on retries, they should include a delivery ID
        header instead of relying on body hashing.
        """
        body_a = b'{"a": 1, "b": 2}'
        body_b = b'{"b": 2, "a": 1}'

        key_a = generate_idempotency_key('src', '', body_a)
        key_b = generate_idempotency_key('src', '', body_b)

        assert key_a != key_b

    def test_source_name_is_namespaced_in_key(self):
        """Keys from different sources with the same body must not collide."""
        body = b'{"event": "test"}'
        key_github = generate_idempotency_key('github', '', body)
        key_stripe  = generate_idempotency_key('stripe', '', body)

        assert key_github != key_stripe
        assert key_github.startswith('github:')
        assert key_stripe.startswith('stripe:')
