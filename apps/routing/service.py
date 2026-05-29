"""
Route matching service.

find_matching_routes() is the core routing function called by the Celery
delivery task. It returns all active routes whose source, event_type, and
JSONPath conditions match the delivery.
"""

from django.db.models import Q

from apps.core.models import Route, Source
from .evaluator import evaluate_conditions


def find_matching_routes(source: Source, event_type: str, payload: dict) -> list[Route]:
    """
    Return all active routes that match this delivery.

    Matching logic (all must be true):
      1. Route.source == source
      2. Route.event_type == event_type OR Route.event_type is blank (wildcard)
      3. evaluate_conditions(payload, route.condition) is True

    Routes are returned in priority order (ascending). All matches are
    returned — delivery is fan-out, not first-match-wins.

    Args:
        source:     The Source model instance for this delivery.
        event_type: Value from the event-type header (e.g. X-GitHub-Event).
        payload:    Parsed JSON payload dict.

    Returns:
        Ordered list of matching Route instances (may be empty).
    """
    candidates = Route.objects.filter(
        source=source,
        is_active=True,
    ).filter(
        Q(event_type=event_type) | Q(event_type='')
    ).select_related('source', 'destination').order_by('priority', 'pk')

    return [
        route for route in candidates
        if evaluate_conditions(payload, route.condition)
    ]
