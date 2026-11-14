from django.db import models
from django.db.models.fields.json import KeyTransform

from .encrypted_password_field import decrypt_password, encrypt_password


def transform_custom_passwords(fields, transform):
    if not isinstance(fields, list):
        return fields

    transformed = []
    for field in fields:
        if (
            isinstance(field, dict)
            and str(field.get("type", "")).strip().lower() == "password"
            and field.get("value")
        ):
            field = {**field, "value": transform(field["value"])}
        transformed.append(field)
    return transformed


class EncryptedCustomFields(models.JSONField):
    """Encrypt password values while retaining the existing JSON structure."""

    def get_prep_value(self, value):
        return transform_custom_passwords(super().get_prep_value(value), encrypt_password)

    def from_db_value(self, value, expression, connection):
        fields = super().from_db_value(value, expression, connection)
        if isinstance(expression, KeyTransform):
            return fields
        return transform_custom_passwords(fields, decrypt_password)
