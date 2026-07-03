from django.utils import timezone

from onikisepet.models import Account, Transaction
from onikisepet.selectors import approved_transactions
from onikisepet.usecases import financial_calculations
from onikisepet.usecases.report_periods import get_month_bounds


def get_dashboard_context(reference_date=None):
    reference_date = reference_date or timezone.localdate()
    month_start, month_end = get_month_bounds(reference_date)

    month_transactions = approved_transactions().filter(
        date__gte=month_start,
        date__lte=month_end,
    )
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
        "month_start": month_start,
        "month_end": month_end,
        "currency_summary": currency_summary,
        "top_expenses": top_expenses,
        "account_balances": account_balances,
    }
