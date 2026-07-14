from django.db.models import Count
from django.urls import reverse

from onikisepet.models import Profile, Transaction

DATA_ENTRY_GROUP = "Data Entry"
VIEWER_GROUP = "Viewer"
APPROVER_GROUP = "Approver"


def _profile_role(user):
    try:
        return user.profile.role
    except Profile.DoesNotExist:
        return None


def _group_fallback_role(user):
    if user.groups.filter(name=DATA_ENTRY_GROUP).exists():
        return Profile.Role.DATA_ENTRY
    if user.groups.filter(name=VIEWER_GROUP).exists():
        return Profile.Role.VIEWER
    return None


def resolve_user_role(user):
    if user.is_superuser:
        return None
    role = _profile_role(user)
    if role is not None:
        return role
    return _group_fallback_role(user)


def can_access_application(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return resolve_user_role(user) is not None


def can_view_reports_and_balances(user):
    return can_access_application(user)


def can_view_operational_pages(user):
    if user.is_superuser:
        return True
    return resolve_user_role(user) == Profile.Role.DATA_ENTRY


def can_view_transaction_list(user):
    if user.is_superuser:
        return True
    return resolve_user_role(user) == Profile.Role.DATA_ENTRY


def can_manage_categories(user):
    return user.is_superuser


def can_manage_accounts(user):
    return user.is_superuser


def can_manage_users(user):
    return user.is_superuser

def can_request_account_changes(user):
    return can_view_operational_pages(user)


def can_create_transactions(user):
    if user.is_superuser:
        return True
    return resolve_user_role(user) == Profile.Role.DATA_ENTRY


def can_edit_transaction(user, transaction):
    if not can_create_transactions(user):
        return False
    if transaction.created_by_id != user.id:
        return False
    return transaction.approval_status in (
        Transaction.ApprovalStatus.PENDING,
        Transaction.ApprovalStatus.REJECTED,
    )


def user_in_approver_group(user):
    return user.groups.filter(name=APPROVER_GROUP).exists()


def can_approve_transactions(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return (
        user_in_approver_group(user)
        and resolve_user_role(user) == Profile.Role.DATA_ENTRY
    )


def can_confirm_bank_import(user):
    return can_approve_transactions(user)


def can_view_reference_data(user):
    if user.is_superuser:
        return True
    if can_view_operational_pages(user):
        return True
    return can_approve_transactions(user)


def can_view_pending_account_change_requests(user):
    return can_approve_transactions(user)


def can_view_pending_bank_imports(user):
    return can_confirm_bank_import(user)


def can_edit_bank_import_preview(user, bank_import):
    if user.is_superuser:
        return True
    return bank_import.uploaded_by_id == user.id


def is_viewer(user):
    if user.is_superuser:
        return False
    return resolve_user_role(user) == Profile.Role.VIEWER


def get_post_login_redirect_url(user):
    if is_viewer(user):
        return reverse("report_dashboard")
    return reverse("home")
