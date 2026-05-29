"""
BaseTransformer defines the interface every transformer must implement.

Subclasses receive the raw parsed payload dict and return a new dict
ready to POST to the destination. They must not mutate the input.
"""

from abc import ABC, abstractmethod


class BaseTransformer(ABC):

    @abstractmethod
    def transform(self, payload: dict) -> dict:
        """
        Transform source payload into the destination's expected shape.

        Args:
            payload: Parsed JSON body from the inbound webhook.

        Returns:
            A new dict to be POSTed to the destination URL.

        Raises:
            KeyError: If required fields are missing from the payload.
                      The Celery task will catch this and retry.
        """
        raise NotImplementedError
