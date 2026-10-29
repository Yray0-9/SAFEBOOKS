from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("safebooks", "0035_financialrecordline_worksheet_amounts")]

    operations = [
        migrations.AddField(
            model_name="financialrecordline",
            name="remarks",
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]
