from django.db import migrations


def delete_reversal_transactions(apps, schema_editor):
    Transaction = apps.get_model("onikisepet", "Transaction")
    Transaction.objects.filter(reverses_transaction__isnull=False).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("onikisepet", "0016_migrate_approver_to_group"),
    ]

    operations = [
        migrations.RunPython(
            delete_reversal_transactions,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="transaction",
            name="reverses_transaction",
        ),
    ]
