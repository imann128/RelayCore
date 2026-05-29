from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _get_fernet():
    key = getattr(settings, 'FIELD_ENCRYPTION_KEY', '')
    if not key:
        raise ValueError(
            "FIELD_ENCRYPTION_KEY is not set in your .env. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


class EncryptedCharField(models.TextField):
    def __init__(self, *args, **kwargs):
        kwargs.pop('max_length', None)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        try:
            return _get_fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            return value

    def get_prep_value(self, value):
        if not value:
            return value
        return _get_fernet().encrypt(value.encode()).decode()