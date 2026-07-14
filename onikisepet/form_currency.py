from django import forms

from onikisepet.models import Account

PRIMARY_ACCOUNT_FIELD_NAMES = (
    "cash_account",
    "bank_account",
    "online_donation_account",
    "source_account",
    "target_account",
)


def account_choice_label(account):
    return f"{account.name} ({account.currency})"


def apply_account_choice_labels(form):
    for field in form.fields.values():
        if not isinstance(field, forms.ModelChoiceField):
            continue
        if getattr(field.queryset, "model", None) is not Account:
            continue
        field.label_from_instance = account_choice_label


def build_transaction_form_currency_context(form):
    account_fields = []
    currencies_by_account_id = {}
    primary_account_field = None

    for name, field in form.fields.items():
        if not isinstance(field, forms.ModelChoiceField):
            continue
        if getattr(field.queryset, "model", None) is not Account:
            continue
        account_fields.append(name)
        for account in field.queryset:
            currencies_by_account_id[str(account.pk)] = account.currency

    if not account_fields:
        return None

    for name in PRIMARY_ACCOUNT_FIELD_NAMES:
        if name in form.fields:
            primary_account_field = name
            break

    if primary_account_field is None:
        primary_account_field = account_fields[0]

    return {
        "account_fields": account_fields,
        "primary_account_field": primary_account_field,
        "currencies_by_account_id": currencies_by_account_id,
    }
