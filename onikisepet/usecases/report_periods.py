from datetime import date, timedelta

from django.utils import timezone


def resolve_report_period(period_value, *, reference_date=None):
    reference_date = reference_date or timezone.localdate()

    if not period_value:
        return None, None, ""

    if period_value == "this_month":
        start = reference_date.replace(day=1)
        if reference_date.month == 12:
            next_month = reference_date.replace(year=reference_date.year + 1, month=1, day=1)
        else:
            next_month = reference_date.replace(month=reference_date.month + 1, day=1)
        end = next_month - timedelta(days=1)
        return start, end, period_value

    if period_value == "last_month":
        first_of_month = reference_date.replace(day=1)
        end = first_of_month - timedelta(days=1)
        start = end.replace(day=1)
        return start, end, period_value

    if period_value == "this_year":
        start = reference_date.replace(month=1, day=1)
        end = reference_date.replace(month=12, day=31)
        return start, end, period_value

    return None, None, ""


PERIOD_LABELS = {
    "this_month": "Bu ay",
    "last_month": "Geçen ay",
    "this_year": "Bu yıl",
}


def get_period_label(period_value):
    return PERIOD_LABELS.get(period_value, "")


def get_month_bounds(reference_date=None):
    start, end, _ = resolve_report_period("this_month", reference_date=reference_date)
    return start, end
