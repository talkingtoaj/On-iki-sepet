from .permissions import (
    can_approve_transactions,
    can_confirm_bank_import,
    can_create_transactions,
    can_manage_accounts,
    can_manage_categories,
    can_manage_users,
    can_request_account_changes,
    can_view_operational_pages,
    can_view_transaction_list,
)
from .selectors import (
    pending_account_change_requests,
    pending_bank_imports,
    pending_transactions,
)


def navigation_permissions(request):
    user = request.user
    if not user.is_authenticated:
        return {}

    context = {
        "can_manage_categories": can_manage_categories(user),
        "can_manage_accounts": can_manage_accounts(user),
        "can_manage_users": can_manage_users(user),
        "can_request_account_changes": can_request_account_changes(user),
        "can_create_transactions": can_create_transactions(user),
        "can_view_operational_pages": can_view_operational_pages(user),
        "can_view_transaction_list": can_view_transaction_list(user),
        "can_approve_transactions": can_approve_transactions(user),
        "current_url_name": getattr(
            getattr(request, "resolver_match", None),
            "url_name",
            "",
        ),
    }
    if can_approve_transactions(user):
        context["pending_approval_count"] = pending_transactions().count()
        context["pending_account_change_count"] = (
            pending_account_change_requests().count()
        )
    if can_confirm_bank_import(user):
        context["pending_import_count"] = pending_bank_imports().count()
    return context
