"""
Tests for find_matching_routes() and evaluate_conditions().

These are the most logic-dense parts of the system — worth testing
thoroughly because a routing bug silently drops deliveries or fans them
out to wrong destinations.

Coverage targets:
  - Exact event_type match
  - Wildcard route (event_type='') matches any event
  - JSONPath condition match (ref = main)
  - JSONPath condition mismatch (ref = dev) → not returned
  - Empty condition dict → always matches
  - Multiple matching routes returned in priority order
  - Inactive routes are excluded
  - Route for a different source is excluded
  - lru_cache: same JSONPath expression reuses cached parse object
"""

import pytest
from functools import lru_cache

from apps.core.models import Route, Source, Destination
from apps.routing.evaluator import evaluate_conditions, _parse_expression
from apps.routing.service import find_matching_routes


# evaluate_conditions unit tests (no DB)

class TestEvaluateConditions:

    def test_empty_conditions_always_match(self, push_payload_main):
        assert evaluate_conditions(push_payload_main, {}) is True

    def test_exact_ref_match(self, push_payload_main):
        assert evaluate_conditions(push_payload_main, {'ref': 'refs/heads/main'}) is True

    def test_ref_mismatch(self, push_payload_dev):
        assert evaluate_conditions(push_payload_dev, {'ref': 'refs/heads/main'}) is False

    def test_multiple_conditions_all_must_match(self, push_payload_main):
        # Both conditions true → match
        assert evaluate_conditions(
            push_payload_main,
            {'ref': 'refs/heads/main', 'pusher.name': 'iman'}
        ) is True

    def test_multiple_conditions_one_fails(self, push_payload_main):
        # ref matches but pusher.name doesn't → no match
        assert evaluate_conditions(
            push_payload_main,
            {'ref': 'refs/heads/main', 'pusher.name': 'someone-else'}
        ) is False

    def test_missing_key_in_payload_does_not_match(self, push_payload_main):
        assert evaluate_conditions(push_payload_main, {'nonexistent.key': 'value'}) is False

    def test_lru_cache_returns_same_parsed_object(self):
        """
        Calling _parse_expression twice with the same string must return the
        identical object (cache hit), not a new parse. We check object identity.
        """
        expr_a = _parse_expression('ref')
        expr_b = _parse_expression('ref')
        assert expr_a is expr_b   # same object from cache, not a re-parse


# find_matching_routes integration tests (requires DB)

@pytest.mark.django_db
class TestFindMatchingRoutes:

    def test_push_to_main_matches_route_with_condition(
        self, github_source, push_to_main_route, push_payload_main
    ):
        routes = find_matching_routes(github_source, 'push', push_payload_main)
        assert len(routes) == 1
        assert routes[0].pk == push_to_main_route.pk

    def test_push_to_dev_does_not_match_main_condition(
        self, github_source, push_to_main_route, push_payload_dev
    ):
        routes = find_matching_routes(github_source, 'push', push_payload_dev)
        assert routes == []

    def test_wildcard_route_matches_any_event_type(
        self, github_source, wildcard_route, push_payload_dev
    ):
        # wildcard_route has event_type='' and condition={}
        routes = find_matching_routes(github_source, 'push', push_payload_dev)
        assert len(routes) == 1
        assert routes[0].pk == wildcard_route.pk

    def test_multiple_routes_returned_in_priority_order(
        self, db, github_source, slack_destination, push_payload_main
    ):
        """When two routes match, lower priority number comes first."""
        low_priority = Route.objects.create(
            source=github_source, event_type='push',
            condition={'ref': 'refs/heads/main'},
            destination=slack_destination,
            transformer_class='github_to_slack',
            priority=5, is_active=True,
        )
        high_priority = Route.objects.create(
            source=github_source, event_type='push',
            condition={'ref': 'refs/heads/main'},
            destination=slack_destination,
            transformer_class='github_to_slack',
            priority=0, is_active=True,
        )
        routes = find_matching_routes(github_source, 'push', push_payload_main)
        assert routes[0].pk == high_priority.pk   # priority=0 is first
        assert routes[1].pk == low_priority.pk

    def test_inactive_route_is_excluded(
        self, db, github_source, slack_destination, push_payload_main
    ):
        Route.objects.create(
            source=github_source, event_type='push',
            condition={}, destination=slack_destination,
            transformer_class='github_to_slack',
            priority=0, is_active=False,   # ← inactive
        )
        routes = find_matching_routes(github_source, 'push', push_payload_main)
        assert routes == []

    def test_route_for_different_source_excluded(
        self, db, github_source, slack_destination, push_payload_main
    ):
        other_source = Source.objects.create(
            name='stripe', slug='stripe-production',
            signature_scheme='none', is_active=True,
        )
        Route.objects.create(
            source=other_source, event_type='push',
            condition={}, destination=slack_destination,
            transformer_class='github_to_slack',
            priority=0, is_active=True,
        )
        # Querying with github_source should not return the stripe route
        routes = find_matching_routes(github_source, 'push', push_payload_main)
        assert routes == []

    def test_event_type_wildcard_and_exact_both_returned(
        self, db, github_source, slack_destination,
        push_to_main_route, wildcard_route, push_payload_main
    ):
        """
        push_to_main_route: event_type='push', condition matches main
        wildcard_route:     event_type='',     no condition

        Both should match a push to main. Priority ordering must hold.
        """
        routes = find_matching_routes(github_source, 'push', push_payload_main)
        pks = [r.pk for r in routes]
        assert push_to_main_route.pk in pks
        assert wildcard_route.pk in pks
        # push_to_main_route has priority=0, wildcard has priority=10
        assert pks.index(push_to_main_route.pk) < pks.index(wildcard_route.pk)
