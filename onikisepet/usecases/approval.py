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


def bulk_approve_transactions(*, user, transaction_ids):
    if not transaction_ids:
        return 0

    pending_transactions = Transaction.objects.filter(
        pk__in=transaction_ids,
        approval_status=Transaction.ApprovalStatus.PENDING,
    ).order_by("pk")

    approved_count = 0
    for transaction in pending_transactions:
        approve_transaction(transaction, user)
        approved_count += 1
    return approved_count


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


def resubmit_transaction(transaction, user):
    before = audit.snapshot_transaction(transaction)
    transaction.approval_status = Transaction.ApprovalStatus.PENDING
    transaction.approved_by = None
    transaction.approved_at = None
    transaction.rejection_reason = ""
    transaction.save(
        update_fields=[
            "approval_status",
            "approved_by",
            "approved_at",
            "rejection_reason",
            "updated_at",
        ]
    )
    audit.log_transaction_resubmit(transaction=transaction, user=user, before=before)
