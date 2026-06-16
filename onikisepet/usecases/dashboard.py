from datetime import date

from django.utils import timezone

from onikisepet.models import Account, Transaction
from onikisepet.usecases import financial_calculations


def _month_bounds(reference_date=None):
    reference_date = reference_date or timezone.localdate()
    start = reference_date.replace(day=1)
    if reference_date.month == 12:
        end = reference_date.replace(year=reference_date.year + 1, month=1, day=1)
    else:
        end = reference_date.replace(month=reference_date.month + 1, day=1)
    from datetime import timedelta

    end = end - timedelta(days=1)
    return start, end


def get_dashboard_context(reference_date=None):
    reference_date = reference_date or timezone.localdate()
    month_start, month_end = _month_bounds(reference_date)

    month_transactions = Transaction.objects.filter(
        date__gte=month_start,
        date__lte=month_end,
    )
    all_transactions = Transaction.objects.all()
    accounts = Account.objects.filter(is_active=True).order_by("name")

    currency_summary = financial_calculations.build_currency_summary(month_transactions)
    expense_by_category = financial_calculations.calculate_expense_totals_by_category(
        month_transactions
    )
    top_expenses = sorted(
        expense_by_category,
        key=lambda item: item["total"],
        reverse=True,
    )[:5]

    account_balances = [
        {
            "account": account,
            "balance": financial_calculations.calculate_account_balance(account),
        }
        for account in accounts
    ]

    return {
        "reference_date": reference_date,
        "month_start": month_start,
        "month_end": month_end,
        "currency_summary": currency_summary,
        "top_expenses": top_expenses,
        "account_balances": account_balances,
        "total_transactions": all_transactions.count(),
    }
