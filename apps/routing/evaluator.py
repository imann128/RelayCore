"""
JSONPath condition evaluator for route matching.

Performance note:
  jsonpath_ng.parse() re-parses the expression string every call.
  With high throughput hitting the same routes, this is wasted CPU.
  Parsed expressions are cached with lru_cache — same string = same object,
  no re-parsing.

Known scaling limit (documented):
  Route candidates are fetched from DB filtered by (source, event_type),
  then conditions are evaluated in Python. This is fine for tens to hundreds
  of routes. If a source grows to thousands of routes, condition evaluation
  should move into Postgres using JSONB operators. This tradeoff is noted
  in the README.
"""

from functools import lru_cache
import jsonpath_ng
import jsonpath_ng.ext  # noqa: F401 — registers extended syntax


@lru_cache(maxsize=256)
def _parse_expression(path: str):
    """
    Parse and cache a JSONPath expression string.

    lru_cache is keyed on the string argument — identical paths return the
    same parsed object without re-parsing. maxsize=256 covers any realistic
    number of distinct condition expressions across all routes.
    """
    return jsonpath_ng.parse(path)


def evaluate_conditions(payload: dict, conditions: dict) -> bool:
    """
    Evaluate all JSONPath conditions against a payload (AND logic).

    All conditions must match for the function to return True.
    An empty conditions dict always returns True (match all).

    Args:
        payload:    Parsed JSON payload dict from the inbound webhook.
        conditions: Dict of {jsonpath_expression: expected_value}.
                    Example: {"ref": "refs/heads/main", "repository.name": "myrepo"}

    Returns:
        True if every condition matches, False otherwise.

    Example:
        >>> evaluate_conditions({"ref": "refs/heads/main"}, {"ref": "refs/heads/main"})
        True
        >>> evaluate_conditions({"ref": "refs/heads/dev"}, {"ref": "refs/heads/main"})
        False
    """
    for json_path, expected_value in conditions.items():
        path_expr = _parse_expression(json_path)
        matches = [match.value for match in path_expr.find(payload)]
        if not matches or matches[0] != expected_value:
            return False
    return True
