from django import forms
from django.utils import timezone

FORM_EXAMPLE_FIELD_VALUES = {
    "cash_income": {
        "donor_name": "Ahmet Yılmaz",
        "amount": "500,00",
        "description": "Pazar ayini bağışı",
    },
    "cash_expense": {
        "payee": "ABC Market",
        "amount": "250,00",
        "description": "Ofis malzemesi",
    },
    "bank_expense": {
        "payee": "Elektrik A.Ş.",
        "amount": "1.200,00",
        "description": "Aylık elektrik faturası",
    },
    "online_donation": {
        "donor_name": "Mehmet Kaya",
        "amount": "300,00",
        "description": "Online platform bağışı",
    },
    "transfer": {
        "amount": "1.000,00",
        "description": "Kasa → banka aktarımı",
    },
}


def _first_choice_value(field):
    if not isinstance(field, forms.ModelChoiceField):
        return None
    first = field.queryset.first()
    return str(first.pk) if first else None


def _choice_label(form, field_name, value):
    field = form.fields.get(field_name)
    if not field or not value:
        return ""
    obj = field.queryset.filter(pk=value).first()
    return str(obj) if obj else ""


def _format_example_summary(guide_key, form, values):
    date = values.get("date", "")
    amount = values.get("amount", "")
    description = values.get("description", "")

    if guide_key == "cash_income":
        category = _choice_label(form, "category", values.get("category"))
        return (
            f"{date} · {values.get('donor_name')} · {amount} TRY · "
            f"{category} · {description}"
        )
    if guide_key == "cash_expense":
        category = _choice_label(form, "category", values.get("category"))
        account = _choice_label(form, "cash_account", values.get("cash_account"))
        return f"{date} · {values.get('payee')} · {amount} TRY · {account} · {category}"
    if guide_key == "bank_expense":
        category = _choice_label(form, "category", values.get("category"))
        account = _choice_label(form, "bank_account", values.get("bank_account"))
        return f"{date} · {values.get('payee')} · {amount} TRY · {account} · {category}"
    if guide_key == "online_donation":
        category = _choice_label(form, "category", values.get("category"))
        account = _choice_label(
            form,
            "online_donation_account",
            values.get("online_donation_account"),
        )
        return (
            f"{date} · {values.get('donor_name')} · {amount} TRY · "
            f"{account} · {category}"
        )
    if guide_key == "transfer":
        source = _choice_label(form, "source_account", values.get("source_account"))
        target = _choice_label(form, "target_account", values.get("target_account"))
        return f"{date} · {amount} TRY · {source} → {target} · {description}"
    return ""


def build_transaction_form_example(form, guide_key):
    static_values = FORM_EXAMPLE_FIELD_VALUES.get(guide_key, {})
    values = {}

    for name, field in form.fields.items():
        if isinstance(field, forms.FileField):
            continue
        if name in static_values:
            values[name] = static_values[name]
        elif name == "date":
            values[name] = timezone.localdate().isoformat()
        else:
            choice_value = _first_choice_value(field)
            if choice_value is not None:
                values[name] = choice_value

    if guide_key == "transfer":
        source_value = values.get("source_account")
        target_value = values.get("target_account")
        if source_value and source_value == target_value:
            target_field = form.fields["target_account"]
            alternate = target_field.queryset.exclude(pk=source_value).first()
            if alternate:
                values["target_account"] = str(alternate.pk)

    has_file_field = any(
        isinstance(field, forms.FileField) for field in form.fields.values()
    )
    return {
        "values": values,
        "summary": _format_example_summary(guide_key, form, values),
        "has_file_field": has_file_field,
    }
