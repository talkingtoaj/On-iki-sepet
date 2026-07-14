from django.db.models import Count

from onikisepet.models import Transaction

FREQUENT_ACCOUNT_ROLE_FIELDS = {
    "income_target": "target_account",
    "expense_source": "source_account",
    "transfer_source": "source_account",
    "transfer_target": "target_account",
}

FREQUENT_ACCOUNT_ROLE_FILTERS = {
    "income_target": {"transaction_type": Transaction.TransactionType.INCOME},
    "expense_source": {"transaction_type": Transaction.TransactionType.EXPENSE},
    "transfer_source": {"transaction_type": Transaction.TransactionType.TRANSFER},
    "transfer_target": {"transaction_type": Transaction.TransactionType.TRANSFER},
}

FREQUENT_ACCOUNT_DEFAULTS_BY_FORM = {
    "CashIncomeForm": {"cash_account": "income_target"},
    "CashExpenseForm": {"cash_account": "expense_source"},
    "BankExpenseForm": {"bank_account": "expense_source"},
    "OnlineDonationIncomeForm": {"online_donation_account": "income_target"},
    "TransferForm": {
        "source_account": "transfer_source",
        "target_account": "transfer_target",
    },
}


def frequent_account_id_for_user(user, role):
    if user is None or not getattr(user, "is_authenticated", False):
        return None

    account_field = FREQUENT_ACCOUNT_ROLE_FIELDS.get(role)
    role_filters = FREQUENT_ACCOUNT_ROLE_FILTERS.get(role)
    if account_field is None or role_filters is None:
        return None

    row = (
        Transaction.objects.filter(
            created_by=user,
            **role_filters,
            **{f"{account_field}__isnull": False},
            **{f"{account_field}__is_active": True},
        )
        .values(account_field)
        .annotate(usage_count=Count("id"))
        .order_by("-usage_count", f"-{account_field}")
        .first()
    )
    if row is None:
        return None
    return row[account_field]


def apply_frequent_account_defaults(form, user):
    field_roles = FREQUENT_ACCOUNT_DEFAULTS_BY_FORM.get(form.__class__.__name__)
    if not field_roles or form.is_bound:
        return

    for field_name, role in field_roles.items():
        if field_name in form.initial:
            continue

        field = form.fields.get(field_name)
        if field is None:
            continue

        account_id = frequent_account_id_for_user(user, role)
        if account_id is None:
            continue

        if field.queryset.filter(pk=account_id).exists():
            form.initial[field_name] = account_id
