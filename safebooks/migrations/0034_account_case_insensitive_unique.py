from django.db import migrations, models
from django.db.models.functions import Upper


class Migration(migrations.Migration):
    dependencies = [
        ("safebooks", "0033_account_session_version"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="bookkeeperaccount",
            constraint=models.UniqueConstraint(Upper("email"), name="bk_email_ci_unique"),
        ),
        migrations.AddConstraint(
            model_name="bookkeeperaccount",
            constraint=models.UniqueConstraint(Upper("username"), name="bk_username_ci_unique"),
        ),
        migrations.AddConstraint(
            model_name="adminaccount",
            constraint=models.UniqueConstraint(Upper("email"), name="admin_email_ci_unique"),
        ),
    ]
