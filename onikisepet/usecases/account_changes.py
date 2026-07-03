from django.core.exceptions import ValidationError
from django.utils import timezone

from onikisepet.models import AccountChangeRequest


def approve_change_request(change_request, approver):
    if change_request.status != AccountChangeRequest.Status.PENDING:
        raise ValidationError("Yalnızca bekleyen hesap değişiklik talepleri onaylanabilir.")

    account = change_request.account
    account.name = change_request.proposed_name
    account.save(update_fields=["name", "updated_at"])

    change_request.status = AccountChangeRequest.Status.APPROVED
    change_request.approved_by = approver
    change_request.approved_at = timezone.now()
    change_request.save(
        update_fields=[
            "status",
            "approved_by",
            "approved_at",
        ]
    )


def reject_change_request(change_request, approver, reason):
    if change_request.status != AccountChangeRequest.Status.PENDING:
        raise ValidationError("Yalnızca bekleyen hesap değişiklik talepleri reddedilebilir.")

    change_request.status = AccountChangeRequest.Status.REJECTED
    change_request.approved_by = approver
    change_request.approved_at = timezone.now()
    change_request.rejection_reason = reason
    change_request.save(
        update_fields=[
            "status",
            "approved_by",
            "approved_at",
            "rejection_reason",
        ]
    )
