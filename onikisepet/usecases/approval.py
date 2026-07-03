from django.utils import timezone

from onikisepet.models import Transaction
from onikisepet.usecases import audit


def initial_approval_status(*, user, transaction_type):
    if transaction_type == Transaction.TransactionType.TRANSFER:
        return Transaction.ApprovalStatus.PENDING
    if user.is_superuser:
        return Transaction.ApprovalStatus.APPROVED
    return Transaction.ApprovalStatus.PENDING


def apply_initial_approval(transaction, user):
    status = initial_approval_status(
        user=user,
        transaction_type=transaction.transaction_type,
    )
    transaction.approval_status = status
    if status == Transaction.ApprovalStatus.APPROVED:
        transaction.approved_by = user
        transaction.approved_at = timezone.now()
    else:
        transaction.approved_by = None
        transaction.approved_at = None


def approve_transaction(transaction, user):
    before = audit.snapshot_transaction(transaction)
    transaction.approval_status = Transaction.ApprovalStatus.APPROVED
    transaction.approved_by = user
    transaction.approved_at = timezone.now()
    transaction.save(
        update_fields=[
            "approval_status",
            "approved_by",
            "approved_at",
            "updated_at",
        ]
    )
    audit.log_transaction_approve(transaction=transaction, user=user, before=before)


def reject_transaction(transaction, user, *, rejection_reason=""):
    before = audit.snapshot_transaction(transaction)
    transaction.approval_status = Transaction.ApprovalStatus.REJECTED
    transaction.approved_by = user
    transaction.approved_at = timezone.now()
    transaction.rejection_reason = rejection_reason
    transaction.save(
        update_fields=[
            "approval_status",
            "approved_by",
            "approved_at",
            "rejection_reason",
            "updated_at",
        ]
    )
    audit.log_transaction_reject(transaction=transaction, user=user, before=before)
