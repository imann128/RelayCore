from .base import BaseTransformer

class PassthroughTransformer(BaseTransformer):
    def transform(self, payload: dict) -> dict:
        return payload