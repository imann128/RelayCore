"""
Shared fixtures for all tests.

Django DB access: mark tests with @pytest.mark.django_db or use the
db fixture. Tests that only hit Redis should use the cache fixture below.
"""

import hashlib
import hmac

import pytest
from django.core.cache import cache

from apps.core.models import Source, Destination, Route

# Cache isolation
@pytest.fixture(autouse=True)
def clear_cache():
    """
    Flush Redis cache before every test.

    Without this, idempotency keys set in one test bleed into the next,
    causing duplicate-detection to fire incorrectly.
    """
    cache.clear()
    yield
    cache.clear()

# Model fixtures
@pytest.fixture
def github_source(db):
    return Source.objects.create(
        name='github',
        slug='github-production',
        secret='test-secret-key',
        signature_scheme='github_hmac',
        is_active=True,
    )


@pytest.fixture
def slack_destination(db):
    return Destination.objects.create(
        name='Slack Engineering',
        url='https://hooks.slack.com/services/TEST/TEST/TEST',
        timeout_seconds=30,
        is_active=True,
    )


@pytest.fixture
def push_to_main_route(db, github_source, slack_destination):
    """Route: GitHub push to main → Slack via GitHubToSlackTransformer."""
    return Route.objects.create(
        source=github_source,
        event_type='push',
        condition={'ref': 'refs/heads/main'},
        destination=slack_destination,
        transformer_class='github_to_slack',
        priority=0,
        is_active=True,
    )


@pytest.fixture
def wildcard_route(db, github_source, slack_destination):
    """Route with no event_type filter and no conditions — matches everything."""
    return Route.objects.create(
        source=github_source,
        event_type='',
        condition={},
        destination=slack_destination,
        transformer_class='github_to_slack',
        priority=10,
        is_active=True,
    )

# Payload fixtures
@pytest.fixture
def push_payload_main():
    return {
        'ref': 'refs/heads/main',
        'pusher': {'name': 'iman'},
        'repository': {'full_name': 'org/repo'},
        'commits': [
            {'id': 'a1b2c3d4e5f6', 'message': 'Fix login bug', 'url': 'https://github.com/commit/a1b2c3d'},
            {'id': 'b2c3d4e5f6a7', 'message': 'Add tests',    'url': 'https://github.com/commit/b2c3d4e'},
        ],
    }


@pytest.fixture
def push_payload_dev():
    return {
        'ref': 'refs/heads/dev',
        'pusher': {'name': 'iman'},
        'repository': {'full_name': 'org/repo'},
        'commits': [
            {'id': 'c3d4e5f6a7b8', 'message': 'WIP', 'url': 'https://github.com/commit/c3d4e5'},
        ],
    }


# HMAC helper
def make_github_signature(secret: str, body: bytes) -> str:
    """Compute the X-Hub-Signature-256 value for a given body and secret."""
    digest = hmac.new(
        key=secret.encode('utf-8'),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"
