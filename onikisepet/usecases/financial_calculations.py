from decimal import Decimal

from django.db.models import Sum

from onikisepet.models import Transaction

DEFAULT_ZERO = Decimal("0.00")


def _aggregate_amount(queryset):
    total = queryset.aggregate(total=Sum("amount"))["total"]
    return total if total is not None else DEFAULT_ZERO


def calculate_income_total(transactions):
    if hasattr(transactions, "filter"):
        return _aggregate_amount(
            transactions.filter(transaction_type=Transaction.TransactionType.INCOME)
        )

    return sum(
        (
            transaction.amount
            for transaction in transactions
            if transaction.transaction_type == Transaction.TransactionType.INCOME
        ),
        DEFAULT_ZERO,
    )


def calculate_expense_total(transactions):
    if hasattr(transactions, "filter"):
        return _aggregate_amount(
            transactions.filter(transaction_type=Transaction.TransactionType.EXPENSE)
        )

    return sum(
        (
            transaction.amount
            for transaction in transactions
            if transaction.transaction_type == Transaction.TransactionType.EXPENSE
        ),
        DEFAULT_ZERO,
    )


def calculate_transfer_total(transactions):
    if hasattr(transactions, "filter"):
        return _aggregate_amount(
            transactions.filter(transaction_type=Transaction.TransactionType.TRANSFER)
        )

    return sum(
        (
            transaction.amount
            for transaction in transactions
            if transaction.transaction_type == Transaction.TransactionType.TRANSFER
        ),
        DEFAULT_ZERO,
    )


def calculate_account_balance(account):
    opening_balance = account.opening_balance or DEFAULT_ZERO
    income_total = _aggregate_amount(
        account.target_transactions.filter(
            transaction_type=Transaction.TransactionType.INCOME
        )
    )
    expense_total = _aggregate_amount(
        account.source_transactions.filter(
            transaction_type=Transaction.TransactionType.EXPENSE
        )
    )
    transfer_in_total = _aggregate_amount(
        account.target_transactions.filter(
            transaction_type=Transaction.TransactionType.TRANSFER
        )
    )
    transfer_out_total = _aggregate_amount(
        account.source_transactions.filter(
            transaction_type=Transaction.TransactionType.TRANSFER
        )
    )

    return (
        opening_balance
        + income_total
        + transfer_in_total
        - expense_total
        - transfer_out_total
    )


def calculate_total_net_position(accounts):
    return sum((calculate_account_balance(account) for account in accounts), DEFAULT_ZERO)
