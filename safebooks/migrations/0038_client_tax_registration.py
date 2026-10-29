from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("safebooks", "0037_financialrecordline_coverage_frequency")]

    operations = [
        migrations.AddField(
            model_name="client",
            name="tax_registration",
            field=models.CharField(
                max_length=16, blank=True, default="",
                choices=[("", "Not set"), ("vat", "VAT"), ("non_vat", "Non-VAT")],
            ),
        ),
    ]
