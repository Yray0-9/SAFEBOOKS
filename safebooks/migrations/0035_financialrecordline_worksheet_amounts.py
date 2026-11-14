from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("safebooks", "0034_account_case_insensitive_unique")]

    operations = [
        migrations.AddField(
            model_name="financialrecordline",
            name=name,
            field=models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True),
        )
        for name in ("mict", "cogs_cos", "income_payments_2307", "tax_withheld")
    ]
