from decimal import Decimal

from django.db.models import Sum

from onikisepet.models import Transaction

DEFAULT_ZERO = Decimal("0.00")
SUPPORTED_CURRENCIES = ("TRY", "USD", "EUR")


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


def calculate_income_total_for_currency(transactions, currency):
    if hasattr(transactions, "filter"):
        return _aggregate_amount(
            transactions.filter(
                transaction_type=Transaction.TransactionType.INCOME,
                currency=currency,
            )
        )

    return sum(
        (
            transaction.amount
            for transaction in transactions
            if transaction.transaction_type == Transaction.TransactionType.INCOME
            and transaction.currency == currency
        ),
        DEFAULT_ZERO,
    )


def calculate_expense_total_for_currency(transactions, currency):
    if hasattr(transactions, "filter"):
        return _aggregate_amount(
            transactions.filter(
                transaction_type=Transaction.TransactionType.EXPENSE,
                currency=currency,
            )
        )

    return sum(
        (
            transaction.amount
            for transaction in transactions
            if transaction.transaction_type == Transaction.TransactionType.EXPENSE
            and transaction.currency == currency
        ),
        DEFAULT_ZERO,
    )


def calculate_net_status_for_currency(transactions, currency):
    return calculate_income_total_for_currency(
        transactions,
        currency,
    ) - calculate_expense_total_for_currency(transactions, currency)


def _calculate_totals_by_category(transactions, transaction_type):
    totals = {}
    iterable = (
        transactions.select_related("category")
        if hasattr(transactions, "select_related")
        else transactions
    )

    for transaction in iterable:
        if transaction.transaction_type != transaction_type or transaction.category is None:
            continue

        key = (transaction.category, transaction.currency)
        totals[key] = totals.get(key, DEFAULT_ZERO) + transaction.amount

    return [
        {
            "category": category,
            "currency": currency,
            "total": total,
        }
        for (category, currency), total in sorted(
            totals.items(),
            key=lambda item: (item[0][0].name, item[0][1]),
        )
    ]


def calculate_income_totals_by_category(transactions):
    return _calculate_totals_by_category(
        transactions,
        Transaction.TransactionType.INCOME,
    )


def calculate_expense_totals_by_category(transactions):
    return _calculate_totals_by_category(
        transactions,
        Transaction.TransactionType.EXPENSE,
    )


def build_currency_summary(transactions):
    return {
        currency: {
            "total_income": calculate_income_total_for_currency(
                transactions,
                currency,
            ),
            "total_expenses": calculate_expense_total_for_currency(
                transactions,
                currency,
            ),
            "net_financial_status": calculate_net_status_for_currency(
                transactions,
                currency,
            ),
        }
        for currency in SUPPORTED_CURRENCIES
    }


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


def calculate_transfer_total_for_currency(transactions, currency):
    if hasattr(transactions, "filter"):
        return _aggregate_amount(
            transactions.filter(
                transaction_type=Transaction.TransactionType.TRANSFER,
                currency=currency,
            )
        )

    return sum(
        (
            transaction.amount
            for transaction in transactions
            if transaction.transaction_type == Transaction.TransactionType.TRANSFER
            and transaction.currency == currency
        ),
        DEFAULT_ZERO,
    )


def build_transfer_summary(transactions):
    return {
        currency: calculate_transfer_total_for_currency(transactions, currency)
        for currency in SUPPORTED_CURRENCIES
    }


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


def calculate_account_balance_for_transactions(account, transactions):
    opening_balance = account.opening_balance or DEFAULT_ZERO

    if hasattr(transactions, "filter"):
        income_total = _aggregate_amount(
            transactions.filter(
                transaction_type=Transaction.TransactionType.INCOME,
                target_account=account,
            )
        )
        expense_total = _aggregate_amount(
            transactions.filter(
                transaction_type=Transaction.TransactionType.EXPENSE,
                source_account=account,
            )
        )
        transfer_in_total = _aggregate_amount(
            transactions.filter(
                transaction_type=Transaction.TransactionType.TRANSFER,
                target_account=account,
            )
        )
        transfer_out_total = _aggregate_amount(
            transactions.filter(
                transaction_type=Transaction.TransactionType.TRANSFER,
                source_account=account,
            )
        )
    else:
        income_total = sum(
            (
                transaction.amount
                for transaction in transactions
                if transaction.transaction_type == Transaction.TransactionType.INCOME
                and transaction.target_account == account
            ),
            DEFAULT_ZERO,
        )
        expense_total = sum(
            (
                transaction.amount
                for transaction in transactions
                if transaction.transaction_type == Transaction.TransactionType.EXPENSE
                and transaction.source_account == account
            ),
            DEFAULT_ZERO,
        )
        transfer_in_total = sum(
            (
                transaction.amount
                for transaction in transactions
                if transaction.transaction_type == Transaction.TransactionType.TRANSFER
                and transaction.target_account == account
            ),
            DEFAULT_ZERO,
        )
        transfer_out_total = sum(
            (
                transaction.amount
                for transaction in transactions
                if transaction.transaction_type == Transaction.TransactionType.TRANSFER
                and transaction.source_account == account
            ),
            DEFAULT_ZERO,
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
