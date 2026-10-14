from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("safebooks", "0032_client_closed_at_client_closure_notes_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="adminaccount",
            name="session_version",
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="bookkeeperaccount",
            name="session_version",
            field=models.PositiveBigIntegerField(default=0),
        ),
    ]
