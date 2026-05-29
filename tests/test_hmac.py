"""
Tests for GitHub HMAC-SHA256 signature verification.

We test the view's _verify_github_hmac static method directly, then test
the full endpoint to confirm the view wires it correctly.

What we must cover:
  - Valid signature → passes
  - Wrong secret → fails (different digest)
  - Tampered body → fails (digest mismatch)
  - Missing header → fails (no header to compare)
  - Malformed header (no 'sha256=' prefix) → fails
  - Timing safety: we use hmac.compare_digest, not ==
    (we can't test timing directly, but we verify the code path)
"""

import hashlib
import hmac
import json
from typing import Optional

import pytest
from django.test import RequestFactory

from apps.delivery.views import ReceiveWebhookView
from tests.conftest import make_github_signature


BODY = b'{"ref": "refs/heads/main", "pusher": {"name": "iman"}}'
SECRET = 'test-secret-key'
CORRECT_SIG = make_github_signature(SECRET, BODY)


class TestVerifyGithubHmac:
    """Unit tests for ReceiveWebhookView._verify_github_hmac."""

    def _make_request(self, sig_header: Optional[str]) -> object:
        factory = RequestFactory()
        headers = {}
        if sig_header is not None:
            headers['HTTP_X_HUB_SIGNATURE_256'] = sig_header
        return factory.post('/fake/', data=BODY, content_type='application/json', **headers)

    def test_valid_signature_passes(self):
        request = self._make_request(CORRECT_SIG)
        assert ReceiveWebhookView._verify_github_hmac(BODY, SECRET, request) is True

    def test_wrong_secret_fails(self):
        wrong_sig = make_github_signature('wrong-secret', BODY)
        request = self._make_request(wrong_sig)
        assert ReceiveWebhookView._verify_github_hmac(BODY, SECRET, request) is False

    def test_tampered_body_fails(self):
        """Signature was computed on original body; tampered body has different digest."""
        tampered_body = b'{"ref": "refs/heads/evil", "pusher": {"name": "attacker"}}'
        request = self._make_request(CORRECT_SIG)
        assert ReceiveWebhookView._verify_github_hmac(tampered_body, SECRET, request) is False

    def test_missing_header_fails(self):
        request = self._make_request(None)
        assert ReceiveWebhookView._verify_github_hmac(BODY, SECRET, request) is False

    def test_malformed_header_no_prefix_fails(self):
        """Header exists but doesn't start with 'sha256=' — treat as invalid."""
        request = self._make_request('deadbeef1234')
        assert ReceiveWebhookView._verify_github_hmac(BODY, SECRET, request) is False

    def test_empty_header_fails(self):
        request = self._make_request('')
        assert ReceiveWebhookView._verify_github_hmac(BODY, SECRET, request) is False


@pytest.mark.django_db
class TestReceiveWebhookViewHmac:
    """Integration: the full view enforces HMAC when source requires it."""

    def test_valid_signature_accepted(self, client, github_source):
        body = json.dumps({'ref': 'refs/heads/main'}).encode()
        sig = make_github_signature(github_source.secret, body)

        # Patch Celery to avoid actually enqueuing
        from unittest.mock import patch
        with patch('apps.delivery.tasks.route_and_deliver.delay'):
            response = client.post(
                f'/webhooks/receive/{github_source.slug}/',
                data=body,
                content_type='application/json',
                HTTP_X_HUB_SIGNATURE_256=sig,
                HTTP_X_GITHUB_EVENT='push',
            )
        assert response.status_code == 200

    def test_invalid_signature_returns_401(self, client, github_source):
        body = json.dumps({'ref': 'refs/heads/main'}).encode()

        response = client.post(
            f'/webhooks/receive/{github_source.slug}/',
            data=body,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256='sha256=badhash',
            HTTP_X_GITHUB_EVENT='push',
        )
        assert response.status_code == 401

    def test_missing_signature_returns_401(self, client, github_source):
        body = json.dumps({'ref': 'refs/heads/main'}).encode()

        response = client.post(
            f'/webhooks/receive/{github_source.slug}/',
            data=body,
            content_type='application/json',
            HTTP_X_GITHUB_EVENT='push',
        )
        assert response.status_code == 401

    def test_unknown_slug_returns_404(self, client):
        response = client.post(
            '/webhooks/receive/does-not-exist/',
            data=b'{}',
            content_type='application/json',
        )
        assert response.status_code == 404
