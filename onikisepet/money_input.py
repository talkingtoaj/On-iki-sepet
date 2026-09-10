"""Parsing and formatting money amounts in either convention.

Turkish writes one thousand two hundred thirty four and fifty six kuruş as
``1.234,56``; plain input writes ``1234.56``. Both are accepted, because
insisting on one convention guarantees somebody will mistype an amount.

Some inputs are ambiguous on their face: is ``1.234`` one thousand two hundred
thirty four, or one point two three four? Two facts about money settle every
such case without guessing:

* a money amount carries at most two decimal places, and
* a thousands group is exactly three digits.

So ``1.234`` can only be thousands, because 1.234 would need three decimal
places. ``1.23`` can only be a decimal, because 23 is not a thousands group.
Anything that satisfies neither reading, such as ``1.2345``, is refused rather
than guessed at.
"""

import re
from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

MAX_DECIMAL_PLACES = 2
THOUSANDS_GROUP_LENGTH = 3

# Currency names and symbols users habitually type after the number.
CURRENCY_SUFFIX = re.compile(
    r"\s*(?:TL|TRY|USD|EUR|₺|\$|€)\s*$", re.IGNORECASE
)
# Ordinary, non-breaking and narrow non-breaking spaces all appear in pasted
# figures and all mean "thousands separator" here.
SPACES = re.compile(r"[\s  ]+")

SEPARATORS = {".", ","}

GROUPING = {
    "tr": (".", ","),
    "en": (",", "."),
}
DEFAULT_GROUPING = GROUPING["tr"]


def _fail(message, value):
    raise ValidationError(message, code="invalid_amount", params={"value": value})


def _split_on(text, separator):
    return text.split(separator)


def _digits_only(groups):
    return all(group.isdigit() for group in groups)


def _from_thousands(groups, original):
    """Join groups that are all valid thousands groups after the first."""
    if not groups[0] or not _digits_only(groups):
        _fail(_("“%(value)s” is not a valid amount."), original)
    if any(len(group) != THOUSANDS_GROUP_LENGTH for group in groups[1:]):
        _fail(_("“%(value)s” is not a valid amount."), original)
    return Decimal("".join(groups))


def _resolve_single_separator(text, separator, original, negative, max_places):
    groups = _split_on(text, separator)

    if len(groups) > 2:
        return _from_thousands(groups, original), negative

    whole, fraction = groups
    if not whole or not fraction or not _digits_only(groups):
        _fail(_("“%(value)s” is not a valid amount."), original)

    # A leading zero before the separator means a fraction of one unit:
    # 0.500 is half, never five hundred.
    if len(fraction) <= max_places or whole.lstrip("0") == "":
        return Decimal(f"{whole}.{fraction}"), negative

    if len(fraction) == THOUSANDS_GROUP_LENGTH:
        return Decimal(whole + fraction), negative

    _fail(_("“%(value)s” is not a valid amount."), original)


def parse_amount(value, max_decimal_places=MAX_DECIMAL_PLACES):
    """A Decimal from either convention, or ValidationError.

    `max_decimal_places` is what disambiguates the tricky shapes, so callers
    that permit more precision get a different and correct reading. With the
    money default of 2, ``1.234`` is one thousand two hundred thirty four,
    because 1.234 would need three decimals. For an exchange rate, which
    allows six, the same text reads as 1.234.
    """
    if value is None:
        _fail(_("An amount is required."), "")

    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))

    original = str(value)
    text = SPACES.sub("", CURRENCY_SUFFIX.sub("", original.strip()))

    if not text:
        _fail(_("An amount is required."), original)

    negative = text.startswith("-")
    text = text.lstrip("+-")

    if not text or not all(character.isdigit() or character in SEPARATORS
                           for character in text):
        _fail(_("“%(value)s” is not a valid amount."), original)

    present = SEPARATORS.intersection(text)

    if not present:
        amount = Decimal(text)
    elif len(present) == 2:
        # Both separators: the rightmost is the decimal point, the other
        # groups thousands.
        decimal_separator = "," if text.rfind(",") > text.rfind(".") else "."
        thousands_separator = "." if decimal_separator == "," else ","
        whole, _sep, fraction = text.rpartition(decimal_separator)
        if not fraction or not fraction.isdigit() or len(fraction) > max_decimal_places:
            _fail(_("“%(value)s” is not a valid amount."), original)
        whole_value = _from_thousands(_split_on(whole, thousands_separator), original)
        amount = Decimal(f"{whole_value}.{fraction}")
    else:
        amount, negative = _resolve_single_separator(
            text, present.pop(), original, negative, max_decimal_places
        )

    try:
        return -amount if negative else amount
    except InvalidOperation:
        _fail(_("“%(value)s” is not a valid amount."), original)


def _group_thousands(digits, separator):
    grouped = []
    while len(digits) > THOUSANDS_GROUP_LENGTH:
        grouped.insert(0, digits[-THOUSANDS_GROUP_LENGTH:])
        digits = digits[:-THOUSANDS_GROUP_LENGTH]
    grouped.insert(0, digits)
    return separator.join(grouped)


def format_amount(value, language=None):
    """Render an amount in the convention for `language`."""
    if value is None or value == "":
        return ""

    if not isinstance(value, Decimal):
        value = Decimal(str(value))

    thousands_separator, decimal_separator = GROUPING.get(
        (language or "")[:2], DEFAULT_GROUPING
    )

    sign = "-" if value < 0 else ""
    quantized = abs(value).quantize(Decimal("0.01"))
    whole, _dot, fraction = f"{quantized:.2f}".partition(".")

    return (
        f"{sign}{_group_thousands(whole, thousands_separator)}"
        f"{decimal_separator}{fraction}"
    )


class MoneyInput(forms.TextInput):
    """Renders an amount in the active language's convention.

    A plain NumberInput would force one convention and reject the other, so
    this is a text input with locale-aware display instead.
    """

    def format_value(self, value):
        if value in (None, ""):
            return ""

        try:
            return format_amount(parse_amount(value), get_language())
        except (ValidationError, InvalidOperation, ArithmeticError):
            # Re-rendering after a validation error: show back exactly what
            # was typed, so the user can see and correct their own input.
            return str(value)


class LocalizedDecimalField(forms.DecimalField):
    """A DecimalField that accepts either numeric convention on input.

    Django's DecimalField accepts only ``1234.56``, which silently rejects the
    way Turkish users write amounts.
    """

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, Decimal):
            return value
        return parse_amount(
            value,
            max_decimal_places=self.decimal_places or MAX_DECIMAL_PLACES,
        )


class MoneyField(LocalizedDecimalField):
    """An amount in currency: two decimal places, locale-aware display."""

    widget = MoneyInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_digits", 12)
        kwargs.setdefault("decimal_places", 2)
        super().__init__(*args, **kwargs)
