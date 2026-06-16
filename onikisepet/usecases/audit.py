from onikisepet.models import AuditLog, Transaction


def _transaction_snapshot(transaction):
    return {
        "date": transaction.date.isoformat(),
        "amount": str(transaction.amount),
        "currency": transaction.currency,
        "transaction_type": transaction.transaction_type,
        "payee": transaction.payee,
        "source_account_id": transaction.source_account_id,
        "target_account_id": transaction.target_account_id,
        "category_id": transaction.category_id,
        "description": transaction.description,
    }


def log_transaction_update(*, transaction, user, before, after):
    AuditLog.objects.create(
        content_type="transaction",
        object_id=transaction.pk,
        action=AuditLog.Action.UPDATE,
        changed_by=user,
        before=before,
        after=after,
    )


def snapshot_transaction(transaction):
    return _transaction_snapshot(transaction)
