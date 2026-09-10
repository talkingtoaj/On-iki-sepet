from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    AccountForm,
    CashExpenseForm,
    CategoryForm,
    ExchangeRateForm,
    TransactionEditForm,
    TransactionForm,
    TransactionVoidForm,
)
from .models import Account, Category, ExchangeRate, Transaction, get_base_currency
from .usecases import audit, cash_ops, financial_calculations

TRANSACTIONS_PER_PAGE = 50


@login_required
@permission_required("onikisepet.view_category", raise_exception=True)
def category_list(request):
    categories = Category.objects.all()
    return render(
        request,
        "onikisepet/category_list.html",
        {"categories": categories},
    )


@login_required
@permission_required("onikisepet.add_category", raise_exception=True)
def category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("category_list")
    else:
        form = CategoryForm()

    return render(
        request,
        "onikisepet/category_form.html",
        {"form": form},
    )


@login_required
@permission_required("onikisepet.view_account", raise_exception=True)
def account_list(request):
    accounts = Account.objects.all()
    return render(
        request,
        "onikisepet/account_list.html",
        {"accounts": accounts},
    )


@login_required
@permission_required("onikisepet.add_account", raise_exception=True)
def account_create(request):
    if request.method == "POST":
        form = AccountForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("account_list")
    else:
        form = AccountForm()

    return render(
        request,
        "onikisepet/account_form.html",
        {"form": form},
    )


@login_required
@permission_required("onikisepet.view_transaction", raise_exception=True)
def transaction_list(request):
    transactions = Transaction.objects.select_related(
        "source_account", "target_account", "category"
    )
    page_obj = Paginator(transactions, TRANSACTIONS_PER_PAGE).get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "onikisepet/transaction_list.html",
        {"transactions": page_obj.object_list, "page_obj": page_obj},
    )


@login_required
@permission_required("onikisepet.view_transaction", raise_exception=True)
def transaction_detail(request, pk):
    transaction = get_object_or_404(
        Transaction.objects.select_related(
            "source_account", "target_account", "category", "created_by"
        ),
        pk=pk,
    )
    return render(
        request,
        "onikisepet/transaction_detail.html",
        {
            "transaction": transaction,
            "receipts": transaction.receipts.all(),
            "audit_logs": transaction.audit_logs.select_related("performed_by"),
        },
    )


@login_required
@permission_required("onikisepet.add_transaction", raise_exception=True)
def transaction_create(request):
    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            audit.create_transaction(form, request.user)
            return redirect("transaction_list")
    else:
        form = TransactionForm()

    return render(
        request,
        "onikisepet/transaction_form.html",
        {"form": form},
    )


@login_required
@permission_required(
    ["onikisepet.add_transaction", "onikisepet.add_receipt"],
    raise_exception=True,
)
def cash_expense_create(request):
    if request.method == "POST":
        form = CashExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            cash_ops.create_cash_transaction(form, request.user)
            return redirect("transaction_list")
    else:
        form = CashExpenseForm()

    return render(
        request,
        "onikisepet/cash_expense_form.html",
        {"form": form},
    )


@login_required
@permission_required("onikisepet.change_transaction", raise_exception=True)
def transaction_edit(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)

    if transaction.is_void:
        raise PermissionDenied("A voided transaction cannot be edited.")

    if request.method == "POST":
        form = TransactionEditForm(request.POST, instance=transaction)
        if form.is_valid():
            audit.update_transaction(
                form, request.user, form.cleaned_data["change_reason"]
            )
            return redirect("transaction_detail", pk=transaction.pk)
    else:
        form = TransactionEditForm(instance=transaction)

    return render(
        request,
        "onikisepet/transaction_edit_form.html",
        {"form": form, "transaction": transaction},
    )


@login_required
@permission_required("onikisepet.void_transaction", raise_exception=True)
def transaction_void(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)

    if transaction.is_void:
        raise PermissionDenied("This transaction is already voided.")

    if request.method == "POST":
        form = TransactionVoidForm(request.POST)
        if form.is_valid():
            audit.void_transaction(
                transaction, request.user, form.cleaned_data["void_reason"]
            )
            return redirect("transaction_detail", pk=transaction.pk)
    else:
        form = TransactionVoidForm()

    return render(
        request,
        "onikisepet/transaction_void_form.html",
        {"form": form, "transaction": transaction},
    )


@login_required
@permission_required("onikisepet.view_exchangerate", raise_exception=True)
def exchange_rate_list(request):
    exchange_rates = ExchangeRate.objects.all()
    return render(
        request,
        "onikisepet/exchange_rate_list.html",
        {
            "exchange_rates": exchange_rates,
            "base_currency": get_base_currency(),
        },
    )


@login_required
@permission_required("onikisepet.add_exchangerate", raise_exception=True)
def exchange_rate_create(request):
    if request.method == "POST":
        form = ExchangeRateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("exchange_rate_list")
    else:
        form = ExchangeRateForm()

    return render(
        request,
        "onikisepet/exchange_rate_form.html",
        {"form": form, "base_currency": get_base_currency()},
    )


@login_required
@permission_required("onikisepet.view_transaction", raise_exception=True)
def report_dashboard(request):
    """Per-currency figures plus a converted grand total.

    Nothing on this page adds two currencies together implicitly. Each currency
    gets its own block, and the only combined numbers are explicitly converted
    at a dated rate whose provenance is shown alongside them.
    """
    as_of = financial_calculations.today()
    transactions = Transaction.objects.all()
    accounts = Account.objects.all()

    currency_summaries = financial_calculations.summarise_by_currency(transactions)
    account_balances = [
        {
            "account": account,
            "balance": financial_calculations.calculate_account_balance(account),
        }
        for account in accounts
    ]

    # Always show the base currency, even with no data, so the page has a
    # meaningful zero state rather than rendering nothing at all.
    shown_currencies = {summary.currency for summary in currency_summaries}
    shown_currencies.update(account.currency for account in accounts)
    shown_currencies.add(get_base_currency())

    summaries_by_currency = {
        summary.currency: summary for summary in currency_summaries
    }
    currency_blocks = [
        summaries_by_currency.get(
            currency,
            financial_calculations.CurrencySummary(
                currency=currency,
                income=financial_calculations.DEFAULT_ZERO,
                expenses=financial_calculations.DEFAULT_ZERO,
                net=financial_calculations.DEFAULT_ZERO,
            ),
        )
        for currency in sorted(
            shown_currencies, key=financial_calculations.currency_sort_key
        )
    ]

    net_grand_total = financial_calculations.calculate_grand_total_in_base(
        {block.currency: block.net for block in currency_blocks},
        on_date=as_of,
    )
    balances_by_currency = (
        financial_calculations.calculate_account_balances_by_currency(accounts)
    )
    balance_grand_total = financial_calculations.calculate_grand_total_in_base(
        balances_by_currency,
        on_date=as_of,
    )

    return render(
        request,
        "onikisepet/report_dashboard.html",
        {
            "as_of": as_of,
            "base_currency": get_base_currency(),
            "currency_blocks": currency_blocks,
            "account_balances": account_balances,
            "net_grand_total": net_grand_total,
            "balance_grand_total": balance_grand_total,
        },
    )
