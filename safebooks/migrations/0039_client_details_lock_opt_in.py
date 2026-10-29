from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("safebooks", "0038_client_tax_registration")]

    # Change the default for new accounts only. Never rewrite saved preferences.
    operations = [
        migrations.AlterField(
            model_name="bookkeeperaccount",
            name="client_details_password_required",
            field=models.BooleanField(default=False),
        ),
    ]
