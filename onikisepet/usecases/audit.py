"""Recording changes to transactions.

Every write to a transaction goes through here so that the audit trail cannot
be bypassed by accident. Values are stored as text because an audit row has to
stay readable even if a category or account is later renamed.
"""

from django.db import transaction as db_transaction

from onikisepet.models import Transaction, TransactionAuditLog

# Fields whose change is worth recording. Bookkeeping timestamps and the void
# flags are excluded: the void action gets its own audit row.
AUDITED_FIELDS = [
    "date",
    "amount",
    "currency",
    "transaction_type",
    "payee",
    "source_account",
    "target_account",
    "category",
    "description",
]


def format_value(value):
    if value is None:
        return ""
    return str(value)


def diff_transactions(previous, current):
    """Fields that differ, as (field_name, old_text, new_text) tuples."""
    changes = []

    for field_name in AUDITED_FIELDS:
        old_value = getattr(previous, field_name)
        new_value = getattr(current, field_name)

        if old_value != new_value:
            changes.append(
                (field_name, format_value(old_value), format_value(new_value))
            )

    return changes


def record_created(transaction, user, reason=""):
    return TransactionAuditLog.objects.create(
        transaction=transaction,
        action=TransactionAuditLog.Action.CREATED,
        reason=reason,
        performed_by=user,
    )


def record_changes(transaction, user, changes, reason):
    """One row per changed field, so the history reads field by field."""
    return [
        TransactionAuditLog.objects.create(
            transaction=transaction,
            action=TransactionAuditLog.Action.CHANGED,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            performed_by=user,
        )
        for field_name, old_value, new_value in changes
    ]


def record_voided(transaction, user, reason):
    return TransactionAuditLog.objects.create(
        transaction=transaction,
        action=TransactionAuditLog.Action.VOIDED,
        reason=reason,
        performed_by=user,
    )


def create_transaction(form, user):
    """Save a new transaction together with its 'created' audit row."""
    with db_transaction.atomic():
        transaction = form.save(commit=False)
        transaction.created_by = user
        transaction.save()
        record_created(transaction, user)

    return transaction


def update_transaction(form, user, reason):
    """Save an edit and record one audit row per changed field.

    The previous state is re-read from the database rather than taken from the
    bound form, because validating the form has already mutated the in-memory
    instance.
    """
    with db_transaction.atomic():
        previous = Transaction.objects.get(pk=form.instance.pk)
        transaction = form.save()
        changes = diff_transactions(previous, transaction)
        record_changes(transaction, user, changes, reason)

    return transaction, changes


def void_transaction(transaction, user, reason):
    """Mark a transaction void. The row is kept; reports exclude it."""
    with db_transaction.atomic():
        transaction.is_void = True
        transaction.void_reason = reason
        transaction.voided_by = user
        transaction.save()
        record_voided(transaction, user, reason)

    return transaction
