"""Date ranges for reports.

Only income and expense figures are period-scoped. Account balances are not,
because a balance is the cumulative position: restricting it to a period would
drop the opening balance and every earlier movement, and report a number that
looks like a balance but is not one.
"""

import calendar
from datetime import date

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

ALL = "all"
THIS_MONTH = "this_month"
LAST_MONTH = "last_month"
THIS_YEAR = "this_year"

# Order as shown in the selector; "all time" first because it is the default.
PERIOD_ORDER = [ALL, THIS_MONTH, LAST_MONTH, THIS_YEAR]

PERIOD_LABELS = {
    ALL: _("All time"),
    THIS_MONTH: _("This month"),
    LAST_MONTH: _("Last month"),
    THIS_YEAR: _("This year"),
}

DEFAULT_PERIOD = ALL


def period_choices():
    return [(value, PERIOD_LABELS[value]) for value in PERIOD_ORDER]


def normalise_period(value):
    """An unrecognised or missing value falls back to all time.

    A bad query string must not silently narrow a report, so the fallback is
    the widest range rather than the narrowest.
    """
    return value if value in PERIOD_LABELS else DEFAULT_PERIOD


def period_label(value):
    return PERIOD_LABELS[normalise_period(value)]


def _month_bounds(year, month):
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def resolve_report_period(value, reference_date=None):
    """Inclusive (start, end) dates, or (None, None) for all time."""
    period = normalise_period(value)
    # Django's configured timezone, not the server clock: the same reason
    # financial_calculations.today() exists.
    today = reference_date or timezone.localdate()

    if period == THIS_MONTH:
        return _month_bounds(today.year, today.month)

    if period == LAST_MONTH:
        year, month = (today.year - 1, 12) if today.month == 1 else (
            today.year,
            today.month - 1,
        )
        return _month_bounds(year, month)

    if period == THIS_YEAR:
        return date(today.year, 1, 1), date(today.year, 12, 31)

    return None, None


def filter_by_period(transactions, value, reference_date=None):
    """Narrow a transaction queryset to the period, inclusive at both ends."""
    start, end = resolve_report_period(value, reference_date=reference_date)

    if start is None:
        return transactions

    return transactions.filter(date__gte=start, date__lte=end)
