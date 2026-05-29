"""
TRANSFORMER_REGISTRY maps string keys to transformer classes.

This module is imported by routing logic only — never by models.py.
Importing it from models.py would create a circular dependency because
these transformer classes may themselves import models.

Adding a new transformer:
  1. Create apps/transformers/your_transformer.py
  2. Add one entry to TRANSFORMER_CHOICES in choices.py
  3. Add one entry here
"""

from .github_to_slack    import GitHubToSlackTransformer
from .github_to_discord  import GitHubToDiscordTransformer
from .calendar_to_db     import CalendarToDatabaseTransformer
from .form_to_email      import FormToEmailTransformer
from .passthrough        import PassthroughTransformer


TRANSFORMER_REGISTRY: dict[str, type] = {
    'github_to_slack':   GitHubToSlackTransformer,
    'github_to_discord': GitHubToDiscordTransformer,
    'calendar_to_db':    CalendarToDatabaseTransformer,
    'form_to_email':     FormToEmailTransformer,
    'passthrough':       PassthroughTransformer,
}


def get_transformer(class_name: str) -> type:
    """
    Look up and return a transformer class by its registry key.

    Raises ValueError for unknown keys — fails fast at task dispatch
    rather than silently dropping the delivery.
    """
    if class_name not in TRANSFORMER_REGISTRY:
        raise ValueError(
            f"Unknown transformer '{class_name}'. "
            f"Available: {list(TRANSFORMER_REGISTRY.keys())}"
        )
    return TRANSFORMER_REGISTRY[class_name]
