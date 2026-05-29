"""
End-to-end integration test — full pipeline in one process.

What this proves:
  POST /webhooks/receive/<slug>/
    → WebhookDelivery row created
    → Celery task executes synchronously (CELERY_TASK_ALWAYS_EAGER=True in test mode)
    → Transformer runs
    → httpx POSTs transformed payload to destination
    → Delivery row status = 'delivered'

We intercept the outbound httpx call with unittest.mock so no real network
traffic occurs and no Slack/Discord account is needed. The mock records
what was posted so we can assert on the transformed payload shape.

Run with:
    pytest tests/test_e2e.py -v
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from apps.core.models import WebhookDelivery
from tests.conftest import make_github_signature


PUSH_BODY = json.dumps({
    'ref': 'refs/heads/main',
    'pusher': {'name': 'iman'},
    'repository': {'full_name': 'iman/webhook-relay'},
    'commits': [
        {'id': 'a1b2c3d4e5f6', 'message': 'docs: add threat model'},
    ],
}).encode()


@pytest.mark.django_db(transaction=True)
class TestEndToEndDelivery:
    """
    Full pipeline: ingest → transform → deliver.

    CELERY_TASK_ALWAYS_EAGER=True (set in settings.py when pytest is active)
    makes .delay() run the task synchronously in the same process, so tests
    can assert on the final DB state without a real Celery worker.
    """

    def _post_webhook(self, client, source, body=PUSH_BODY, event='push'):
        sig = make_github_signature(source.secret, body)
        return client.post(
            f'/webhooks/receive/{source.slug}/',
            data=body,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=sig,
            HTTP_X_GITHUB_EVENT=event,
        )

    def test_full_pipeline_delivers_and_updates_status(
        self, client, github_source, push_to_main_route
    ):
        """
        Happy path: valid push event → delivery row created → task runs →
        httpx posts to destination → status becomes 'delivered'.
        """
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch('apps.delivery.tasks.httpx.post', return_value=mock_response) as mock_post:
            response = self._post_webhook(client, github_source)

        assert response.status_code == 200
        data = response.json()
        assert 'delivery_id' in data

        delivery = WebhookDelivery.objects.get(pk=data['delivery_id'])
        assert delivery.status == 'delivered'

        # Transformer must have shaped the payload into a Slack message
        assert mock_post.called
        posted_payload = mock_post.call_args.kwargs.get('json') or mock_post.call_args[1].get('json')
        assert 'text' in posted_payload
        assert 'iman' in posted_payload['text']
        assert 'iman/webhook-relay' in posted_payload['text']

    def test_duplicate_event_is_dropped(
        self, client, github_source, push_to_main_route
    ):
        """
        Sending the exact same payload twice: first is accepted, second is
        detected as duplicate and no delivery task is run for it.
        """
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch('apps.delivery.tasks.httpx.post', return_value=mock_response) as mock_post:
            r1 = self._post_webhook(client, github_source)
            r2 = self._post_webhook(client, github_source)  # identical body

        assert r1.status_code == 200
        assert r1.json().get('status') == 'accepted'

        assert r2.status_code == 200
        assert r2.json().get('status') == 'duplicate'

        # httpx must only have been called once — for the first event only
        assert mock_post.call_count == 1

    def test_sig_failed_delivery_is_logged(self, client, github_source):
        """
        A request with a bad signature is rejected (401) and a
        WebhookDelivery row with status='sig_failed' is written for audit.
        """
        response = client.post(
            f'/webhooks/receive/{github_source.slug}/',
            data=PUSH_BODY,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256='sha256=badhash',
            HTTP_X_GITHUB_EVENT='push',
        )
        assert response.status_code == 401

        row = WebhookDelivery.objects.filter(
            source=github_source, status='sig_failed'
        ).last()
        assert row is not None

    def test_no_matching_route_still_marks_delivered(
        self, client, github_source
    ):
        """
        An event with no matching route should still reach 'delivered' —
        the system accepted it; there is simply nothing to fan out to.
        """
        body = json.dumps({
            'ref': 'refs/heads/feature',   # no route condition matches this
            'pusher': {'name': 'iman'},
            'repository': {'full_name': 'iman/webhook-relay'},
            'commits': [],
        }).encode()

        with patch('apps.delivery.tasks.httpx.post') as mock_post:
            response = self._post_webhook(client, github_source, body=body)

        assert response.status_code == 200
        delivery = WebhookDelivery.objects.get(pk=response.json()['delivery_id'])
        assert delivery.status == 'delivered'
        assert not mock_post.called   # no destination was hit
