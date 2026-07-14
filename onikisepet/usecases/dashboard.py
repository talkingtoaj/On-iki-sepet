from django.utils import timezone

from onikisepet.models import Account, Transaction
from onikisepet.selectors import (
    approved_transactions,
    pending_account_change_requests,
    pending_bank_imports,
    pending_transactions,
)
from onikisepet.usecases import financial_calculations
from onikisepet.usecases.report_periods import get_month_bounds

APPROVER_PREVIEW_LIMIT = 5


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


def get_approver_panel_context(limit=APPROVER_PREVIEW_LIMIT):
    pending_tx_qs = pending_transactions().select_related(
        "source_account",
        "target_account",
        "category",
        "created_by",
    )
    return {
        "pending_transaction_count": pending_tx_qs.count(),
        "pending_transactions_preview": pending_tx_qs.order_by("-date", "-id")[:limit],
        "pending_account_change_count": pending_account_change_requests().count(),
        "pending_import_count": pending_bank_imports().count(),
    }


def get_operator_context(user):
    pending_count = Transaction.objects.filter(
        created_by=user,
        approval_status=Transaction.ApprovalStatus.PENDING,
    ).count()
    return {"my_pending_transaction_count": pending_count}


def get_home_context(user, reference_date=None):
    context = get_dashboard_context(reference_date=reference_date)
    context.update(get_operator_context(user))
    return context
