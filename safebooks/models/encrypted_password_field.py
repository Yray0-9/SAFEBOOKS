from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


@lru_cache(maxsize=4)
def _cipher(key):
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeError):
        raise ImproperlyConfigured(
            "Set SAFEBOOKS_CLIENT_CREDENTIAL_KEY to a valid Fernet key."
        ) from None


def encrypt_password(value):
    if not value:
        return value
    return _cipher(settings.CLIENT_CREDENTIAL_KEY).encrypt(value.encode("utf-8")).decode("ascii")


class EncryptedPasswordField(models.CharField):
    """Keep the plaintext input limit while using a text column for ciphertext."""

    def db_type(self, connection):
        return models.TextField().db_type(connection)

    def get_prep_value(self, value):
        return encrypt_password(super().get_prep_value(value))

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        try:
            return _cipher(settings.CLIENT_CREDENTIAL_KEY).decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeError):
            raise ValueError("Could not decrypt a saved client credential.") from None
