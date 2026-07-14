from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("onikisepet", "0018_load_kut_seed_data"),
    ]

    operations = [
        migrations.AlterField(
            model_name="auditlog",
            name="action",
            field=models.CharField(
                choices=[
                    ("create", "Create"),
                    ("update", "Update"),
                    ("approve", "Approve"),
                    ("reject", "Reject"),
                    ("resubmit", "Resubmit"),
                ],
                max_length=10,
            ),
        ),
    ]
