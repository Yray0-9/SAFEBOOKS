from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("safebooks", "0036_financialrecordline_remarks")]

    operations = [
        migrations.AddField(
            model_name="financialrecordline",
            name="coverage_frequency",
            field=models.CharField(
                max_length=16, null=True, blank=True,
                choices=[("monthly", "Monthly"), ("quarterly", "Quarterly"), ("annually", "Annually")],
            ),
        ),
    ]
