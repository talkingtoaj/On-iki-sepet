from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("onikisepet", "0011_bank_statement_import"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="role",
            field=models.CharField(
                choices=[
                    ("viewer", "Viewer"),
                    ("data_entry", "Data Entry"),
                    ("approver", "Approver"),
                ],
                default="viewer",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="rejection_reason",
            field=models.TextField(blank=True),
        ),
    ]
