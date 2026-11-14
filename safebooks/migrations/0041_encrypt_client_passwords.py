from django.db import migrations, models

from safebooks.models.encrypted_password_field import EncryptedPasswordField, encrypt_password


def encrypt_existing_passwords(apps, schema_editor):
    Client = apps.get_model("safebooks", "Client")
    clients = Client.objects.using(schema_editor.connection.alias)
    fields = ["email_password", "orus_password"]
    last_id = 0
    while batch := list(clients.filter(pk__gt=last_id).only("id", *fields).order_by("id")[:500]):
        last_id = batch[-1].pk
        populated = [client for client in batch if client.email_password or client.orus_password]
        for client in populated:
            client.email_password = encrypt_password(client.email_password)
            client.orus_password = encrypt_password(client.orus_password)
        clients.bulk_update(populated, fields)


class Migration(migrations.Migration):
    dependencies = [("safebooks", "0040_bookkeeper_verification_proof")]

    operations = [
        migrations.AlterField("client", "email_password", models.TextField(blank=True, default="")),
        migrations.AlterField("client", "orus_password", models.TextField(blank=True, default="")),
        migrations.RunPython(encrypt_existing_passwords),
        migrations.SeparateDatabaseAndState(state_operations=[
            migrations.AlterField("client", "email_password", EncryptedPasswordField(max_length=255, blank=True, default="")),
            migrations.AlterField("client", "orus_password", EncryptedPasswordField(max_length=255, blank=True, default="")),
        ]),
    ]
