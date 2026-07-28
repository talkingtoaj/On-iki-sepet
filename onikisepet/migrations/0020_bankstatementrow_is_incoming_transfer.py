from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("onikisepet", "0019_auditlog_resubmit_action"),
    ]

    operations = [
        migrations.AddField(
            model_name="bankstatementrow",
            name="is_incoming_transfer",
            field=models.BooleanField(default=False),
        ),
    ]
