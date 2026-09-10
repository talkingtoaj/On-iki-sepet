"""Financial totals and balances.

The central rule here is that amounts in different currencies are not
commensurable. Every total is therefore either scoped to one currency, grouped
by currency, or explicitly converted at a dated exchange rate. The helpers that
return a single bare number refuse to run on mixed-currency data rather than
returning a meaningless sum.
"""

from dataclasses import dataclass
from datetime import date as date_type
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Sum
from django.utils import timezone

from onikisepet.models import ExchangeRate, Transaction, get_base_currency

DEFAULT_ZERO = Decimal("0.00")
CENTS = Decimal("0.01")


def today():
    """Today according to Django's configured TIME_ZONE.

    `date.today()` reads the server's own clock instead, so a machine in a
    different zone could pick the wrong day's exchange rate and value a report
    at yesterday's or tomorrow's figures.
    """
    return timezone.localdate()


class MixedCurrencyError(ValueError):
    """Raised when a single total would span more than one currency."""


@dataclass(frozen=True)
class CurrencySummary:
    currency: str
    income: Decimal
    expenses: Decimal
    net: Decimal


@dataclass(frozen=True)
class CurrencyConversion:
    currency: str
    amount: Decimal
    rate: Decimal | None
    rate_date: date_type | None
    converted: Decimal | None

    @property
    def is_convertible(self):
        return self.converted is not None


@dataclass(frozen=True)
class GrandTotal:
    base_currency: str
    total: Decimal
    conversions: list[CurrencyConversion]
    missing_currencies: list[str]

    @property
    def is_complete(self):
        return not self.missing_currencies


def _is_queryset(transactions):
    return hasattr(transactions, "filter")


def _exclude_voided(transactions):
    """Voided transactions are kept for the audit trail but never counted.

    The exclusion lives here, at the bottom of every calculation, so that no
    caller can produce a total that includes a voided row by forgetting to
    filter it out.
    """
    if _is_queryset(transactions):
        return transactions.filter(is_void=False)
    return [transaction for transaction in transactions if not transaction.is_void]


def _filter_type(transactions, transaction_type):
    transactions = _exclude_voided(transactions)

    if _is_queryset(transactions):
        return transactions.filter(transaction_type=transaction_type)
    return [
        transaction
        for transaction in transactions
        if transaction.transaction_type == transaction_type
    ]


def _filter_currency(transactions, currency):
    if _is_queryset(transactions):
        return transactions.filter(currency=currency)
    return [
        transaction for transaction in transactions if transaction.currency == currency
    ]


def _aggregate_amount(transactions):
    if _is_queryset(transactions):
        total = transactions.aggregate(total=Sum("amount"))["total"]
        return total if total is not None else DEFAULT_ZERO
    return sum((transaction.amount for transaction in transactions), DEFAULT_ZERO)


def _currencies_present(transactions):
    if _is_queryset(transactions):
        return set(transactions.values_list("currency", flat=True))
    return {transaction.currency for transaction in transactions}


def currency_sort_key(currency):
    """Base currency first, then alphabetical, so reports read consistently."""
    return (currency != get_base_currency(), currency)


def _single_currency_total(transactions, transaction_type, currency, label):
    selected = _filter_type(transactions, transaction_type)

    if currency is not None:
        return _aggregate_amount(_filter_currency(selected, currency))

    present = _currencies_present(selected)
    if len(present) > 1:
        raise MixedCurrencyError(
            f"Cannot produce a single {label} total across "
            f"{', '.join(sorted(present))}. Pass currency=..., or use "
            f"calculate_{label}_total_by_currency()."
        )

    return _aggregate_amount(selected)


def _totals_by_currency(transactions, transaction_type):
    selected = _filter_type(transactions, transaction_type)

    if _is_queryset(selected):
        rows = selected.values("currency").annotate(total=Sum("amount"))
        return {row["currency"]: row["total"] for row in rows}

    totals: dict[str, Decimal] = {}
    for transaction in selected:
        totals[transaction.currency] = (
            totals.get(transaction.currency, DEFAULT_ZERO) + transaction.amount
        )
    return totals


def calculate_income_total(transactions, currency=None):
    return _single_currency_total(
        transactions, Transaction.TransactionType.INCOME, currency, "income"
    )


def calculate_expense_total(transactions, currency=None):
    return _single_currency_total(
        transactions, Transaction.TransactionType.EXPENSE, currency, "expense"
    )


def calculate_transfer_total(transactions, currency=None):
    return _single_currency_total(
        transactions, Transaction.TransactionType.TRANSFER, currency, "transfer"
    )


def calculate_income_total_by_currency(transactions):
    return _totals_by_currency(transactions, Transaction.TransactionType.INCOME)


def calculate_expense_total_by_currency(transactions):
    return _totals_by_currency(transactions, Transaction.TransactionType.EXPENSE)


def calculate_transfer_total_by_currency(transactions):
    return _totals_by_currency(transactions, Transaction.TransactionType.TRANSFER)


def summarise_by_currency(transactions):
    """Income, expenses and net per currency. Transfers are deliberately not
    part of income, expenses or net; they only move money between accounts.
    """
    income = calculate_income_total_by_currency(transactions)
    expenses = calculate_expense_total_by_currency(transactions)
    transfers = calculate_transfer_total_by_currency(transactions)

    currencies = sorted(
        set(income) | set(expenses) | set(transfers), key=currency_sort_key
    )

    summaries = []
    for currency in currencies:
        currency_income = income.get(currency, DEFAULT_ZERO)
        currency_expenses = expenses.get(currency, DEFAULT_ZERO)
        summaries.append(
            CurrencySummary(
                currency=currency,
                income=currency_income,
                expenses=currency_expenses,
                net=currency_income - currency_expenses,
            )
        )
    return summaries


def calculate_account_balance(account):
    opening_balance = account.opening_balance or DEFAULT_ZERO
    incoming = account.target_transactions.filter(is_void=False)
    outgoing = account.source_transactions.filter(is_void=False)

    income_total = _aggregate_amount(
        incoming.filter(transaction_type=Transaction.TransactionType.INCOME)
    )
    expense_total = _aggregate_amount(
        outgoing.filter(transaction_type=Transaction.TransactionType.EXPENSE)
    )
    transfer_in_total = _aggregate_amount(
        incoming.filter(transaction_type=Transaction.TransactionType.TRANSFER)
    )
    transfer_out_total = _aggregate_amount(
        outgoing.filter(transaction_type=Transaction.TransactionType.TRANSFER)
    )

    return (
        opening_balance
        + income_total
        + transfer_in_total
        - expense_total
        - transfer_out_total
    )


def calculate_account_balances_by_currency(accounts):
    balances: dict[str, Decimal] = {}
    for account in accounts:
        balances[account.currency] = balances.get(
            account.currency, DEFAULT_ZERO
        ) + calculate_account_balance(account)
    return balances


def calculate_total_net_position(accounts, currency=None):
    balances = calculate_account_balances_by_currency(accounts)

    if currency is not None:
        return balances.get(currency, DEFAULT_ZERO)

    if len(balances) > 1:
        raise MixedCurrencyError(
            "Cannot produce a single net position across "
            f"{', '.join(sorted(balances))}. Pass currency=..., or use "
            "calculate_grand_total_in_base()."
        )

    return next(iter(balances.values()), DEFAULT_ZERO)


def convert_to_base(amount, currency, on_date=None):
    """Value `amount` in the base currency, or None if no rate is known."""
    on_date = on_date or today()
    rate = ExchangeRate.rate_for(currency, on_date)

    if rate is None:
        return None

    return (amount * rate).quantize(CENTS, rounding=ROUND_HALF_UP)


def calculate_grand_total_in_base(amounts_by_currency, on_date=None):
    """Convert per-currency amounts into one base-currency figure.

    Currencies with no usable rate are listed in `missing_currencies` and left
    out of the total. Callers must surface that, because an incomplete total
    presented as complete would understate the real position.
    """
    on_date = on_date or today()
    base_currency = get_base_currency()

    conversions: list[CurrencyConversion] = []
    missing_currencies: list[str] = []
    total = DEFAULT_ZERO

    for currency in sorted(amounts_by_currency, key=currency_sort_key):
        amount = amounts_by_currency[currency]

        if currency == base_currency:
            rate, rate_date = Decimal("1"), None
        else:
            quote = ExchangeRate.quote_for(currency, on_date)
            rate = quote.rate_to_base if quote else None
            rate_date = quote.effective_date if quote else None

        if rate is None:
            missing_currencies.append(currency)
            conversions.append(
                CurrencyConversion(
                    currency=currency,
                    amount=amount,
                    rate=None,
                    rate_date=None,
                    converted=None,
                )
            )
            continue

        converted = (amount * rate).quantize(CENTS, rounding=ROUND_HALF_UP)
        total += converted
        conversions.append(
            CurrencyConversion(
                currency=currency,
                amount=amount,
                rate=rate,
                rate_date=rate_date,
                converted=converted,
            )
        )

    return GrandTotal(
        base_currency=base_currency,
        total=total,
        conversions=conversions,
        missing_currencies=missing_currencies,
    )
