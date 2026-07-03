from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("onikisepet", "0012_approver_role_and_rejection_reason"),
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
                ],
                max_length=10,
            ),
        ),
    ]
