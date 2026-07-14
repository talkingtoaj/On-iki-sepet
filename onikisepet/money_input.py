import re
from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError

CURRENCY_SUFFIX_PATTERN = re.compile(r"\s*(?:TL|TRY|USD|EUR)\s*$", re.IGNORECASE)


def parse_localized_decimal(value):
    if value is None:
        raise ValidationError("Tutar boş olamaz.")

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        return Decimal(str(value))

    text = str(value).strip()
    if not text:
        raise ValidationError("Tutar boş olamaz.")

    text = CURRENCY_SUFFIX_PATTERN.sub("", text)
    normalized = text.replace(" ", "")
    if "," in normalized and "." in normalized:
        if normalized.rfind(",") > normalized.rfind("."):
            normalized = normalized.replace(".", "").replace(",", ".")
        else:
            normalized = normalized.replace(",", "")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")

    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValidationError(f"Geçersiz tutar: {text}") from exc


def format_turkish_decimal(value):
    if value in (None, ""):
        return ""

    if not isinstance(value, Decimal):
        value = Decimal(str(value))

    sign = "-" if value < 0 else ""
    quantized = abs(value).quantize(Decimal("0.01"))
    integer_part, _, fractional_part = f"{quantized:.2f}".partition(".")
    grouped_integer = _group_thousands(integer_part)
    return f"{sign}{grouped_integer},{fractional_part}"


def _group_thousands(integer_part):
    if len(integer_part) <= 3:
        return integer_part

    groups = []
    while integer_part:
        groups.append(integer_part[-3:])
        integer_part = integer_part[:-3]
    return ".".join(reversed(groups))


class TurkishMoneyInput(forms.TextInput):
    def __init__(self, attrs=None):
        merged_attrs = {
            "inputmode": "decimal",
            "autocomplete": "off",
            "data-transaction-amount-input": "true",
        }
        if attrs:
            merged_attrs.update(attrs)
        super().__init__(attrs=merged_attrs)


class TurkishMoneyDecimalField(forms.DecimalField):
    default_error_messages = {
        "invalid": "Geçerli bir tutar girin (örn. 1.250,50).",
    }

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", TurkishMoneyInput())
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, Decimal):
            return value
        try:
            return parse_localized_decimal(value)
        except ValidationError as exc:
            raise ValidationError(
                self.error_messages["invalid"],
                code="invalid",
            ) from exc
