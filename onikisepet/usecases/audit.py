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
        "approval_status": transaction.approval_status,
        "rejection_reason": transaction.rejection_reason,
    }


def _create_audit_log(*, transaction, user, action, before, after):
    AuditLog.objects.create(
        content_type="transaction",
        object_id=transaction.pk,
        action=action,
        changed_by=user,
        before=before,
        after=after,
    )


def log_transaction_create(*, transaction, user):
    _create_audit_log(
        transaction=transaction,
        user=user,
        action=AuditLog.Action.CREATE,
        before={},
        after=_transaction_snapshot(transaction),
    )


def log_transaction_update(*, transaction, user, before, after):
    _create_audit_log(
        transaction=transaction,
        user=user,
        action=AuditLog.Action.UPDATE,
        before=before,
        after=after,
    )


def log_transaction_approve(*, transaction, user, before):
    _create_audit_log(
        transaction=transaction,
        user=user,
        action=AuditLog.Action.APPROVE,
        before=before,
        after=_transaction_snapshot(transaction),
    )


def log_transaction_reject(*, transaction, user, before):
    _create_audit_log(
        transaction=transaction,
        user=user,
        action=AuditLog.Action.REJECT,
        before=before,
        after=_transaction_snapshot(transaction),
    )


def log_transaction_resubmit(*, transaction, user, before):
    _create_audit_log(
        transaction=transaction,
        user=user,
        action=AuditLog.Action.RESUBMIT,
        before=before,
        after=_transaction_snapshot(transaction),
    )


def snapshot_transaction(transaction):
    return _transaction_snapshot(transaction)
