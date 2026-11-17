from django.db import migrations

from safebooks.models.encrypted_custom_fields import EncryptedCustomFields, transform_custom_passwords
from safebooks.models.encrypted_password_field import decrypt_password, encrypt_password


def encrypt_unencrypted_password(value):
    # The live app may have saved ciphertext before this migration runs.
    try:
        decrypt_password(value)
    except ValueError:
        return encrypt_password(value)
    return value


def encrypt_existing_custom_passwords(apps, schema_editor):
    Client = apps.get_model("safebooks", "Client")
    clients = Client.objects.using(schema_editor.connection.alias)
    locked_clients = clients.select_for_update().only("id", "custom_fields").order_by("id")
    last_id = 0
    while batch := list(locked_clients.filter(pk__gt=last_id)[:500]):
        last_id = batch[-1].pk
        updated = []
        for client in batch:
            fields = transform_custom_passwords(client.custom_fields, encrypt_unencrypted_password)
            if fields != client.custom_fields:
                client.custom_fields = fields
                updated.append(client)
        clients.bulk_update(updated, ["custom_fields"])


class Migration(migrations.Migration):
    dependencies = [("safebooks", "0041_encrypt_client_passwords")]

    operations = [
        migrations.RunPython(encrypt_existing_custom_passwords),
        migrations.SeparateDatabaseAndState(state_operations=[
            migrations.AlterField("client", "custom_fields", EncryptedCustomFields(blank=True, default=list)),
        ]),
    ]
