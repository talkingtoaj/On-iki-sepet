from django.db import migrations


def load_kut_seed_data(apps, schema_editor):
    from onikisepet.bootstrap import bootstrap_kut

    bootstrap_kut()


class Migration(migrations.Migration):

    dependencies = [
        ("onikisepet", "0017_remove_transaction_reverses_transaction"),
    ]

    operations = [
        migrations.RunPython(
            load_kut_seed_data,
            migrations.RunPython.noop,
        ),
    ]
