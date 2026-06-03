from django.db import transaction as db_transaction
from onikisepet.models import Transaction, Receipt

def create_cash_transaction(form, user):
    with db_transaction.atomic():
        transaction_data = form.get_transaction_data()
        transaction_data["created_by"] = user
        created_transaction = Transaction.objects.create(**transaction_data)
        Receipt.objects.create(
            transaction=created_transaction,
            file=form.get_receipt_file(),
            original_filename=form.get_original_filename(),
            uploaded_by=user,
        )