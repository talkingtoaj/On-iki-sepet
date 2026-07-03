from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("onikisepet", "0014_accountchangerequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="reverses_transaction",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="reversal_transactions",
                to="onikisepet.transaction",
            ),
        ),
    ]
