from django.db import transaction as db_transaction

from onikisepet.models import Receipt, Transaction
from onikisepet.usecases import approval, audit


def create_cash_transaction(form, user):
    with db_transaction.atomic():
        transaction_data = form.get_transaction_data()
        created_transaction = Transaction(
            **transaction_data,
            created_by=user,
        )
        approval.apply_initial_approval(created_transaction, user)
        created_transaction.save()
        audit.log_transaction_create(transaction=created_transaction, user=user)
        receipt_file = form.cleaned_data["receipt_file"]
        Receipt.objects.create(
            transaction=created_transaction,
            file=receipt_file,
            original_filename=receipt_file.name,
            uploaded_by=user,
        )
    return created_transaction
