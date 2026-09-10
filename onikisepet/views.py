import contextlib

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from .forms import (
    AccountForm,
    BankStatementUploadForm,
    CashExpenseForm,
    CategoryForm,
    ExchangeRateForm,
    TransactionEditForm,
    TransactionForm,
    TransactionVoidForm,
)
from .models import (
    Account,
    BankStatementImport,
    Category,
    ExchangeRate,
    Transaction,
    get_base_currency,
)
from .usecases import (
    audit,
    bank_import,
    bank_ops,
    cash_ops,
    financial_calculations,
    report_periods,
)

TRANSACTIONS_PER_PAGE = 50


def permission_denied(request, exception=None):
    """Explain a refusal rather than showing a bare 403.

    A brand-new account holds no role, so it is refused everywhere. Telling
    that user their access is still pending is far more useful than a blank
    "Forbidden", while a user who does have a role and simply lacks one
    permission gets the ordinary refusal. The status stays 403 either way: the
    page explains the situation, it does not grant anything.
    """
    user = request.user
    has_a_role = user.is_authenticated and (
        user.is_superuser or user.groups.exists()
    )
    template = (
        "onikisepet/403.html" if has_a_role else "onikisepet/pending_access.html"
    )
    return render(request, template, status=403)


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
        raise PermissionDenied(_("A voided transaction cannot be edited."))

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
        raise PermissionDenied(_("This transaction is already voided.")) 

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
def record_type_guide(request):
    """Explains which of the three record kinds to use. Static content, so no
    context beyond what the base template needs.
    """
    return render(request, "onikisepet/record_type_guide.html")


@login_required
@permission_required("onikisepet.view_transaction", raise_exception=True)
def finance_guide(request):
    return render(
        request,
        "onikisepet/finance_guide.html",
        {"base_currency": get_base_currency()},
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
    accounts = Account.objects.all()

    period = report_periods.normalise_period(request.GET.get("period"))
    # Income and expenses are period-scoped; balances below are not, because a
    # balance is cumulative and a scoped one would omit the opening position.
    period_transactions = report_periods.filter_by_period(
        Transaction.objects.all(), period, reference_date=as_of
    )

    currency_summaries = financial_calculations.summarise_by_currency(
        period_transactions
    )
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
            "period": period,
            "period_label": report_periods.period_label(period),
            "period_choices": report_periods.period_choices(),
            "currency_blocks": currency_blocks,
            "account_balances": account_balances,
            "net_grand_total": net_grand_total,
            "balance_grand_total": balance_grand_total,
        },
    )


IMPORT_PERMISSIONS = ["onikisepet.add_transaction", "onikisepet.view_transaction"]


@login_required
@permission_required("onikisepet.view_transaction", raise_exception=True)
def import_list(request):
    imports = BankStatementImport.objects.select_related(
        "account", "uploaded_by"
    )
    return render(
        request,
        "onikisepet/import_list.html",
        {"statement_imports": imports},
    )


@login_required
@permission_required(IMPORT_PERMISSIONS, raise_exception=True)
def import_new(request):
    """Upload and parse. Creates draft rows only; nothing is posted yet."""
    error = None

    if request.method == "POST":
        form = BankStatementUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                statement_import = bank_ops.create_draft_import(
                    account=form.cleaned_data["account"],
                    uploaded_file=form.cleaned_data["statement_file"],
                    user=request.user,
                )
            except bank_import.StatementFormatError as exc:
                error = str(exc)
            else:
                return redirect("import_preview", pk=statement_import.pk)
    else:
        form = BankStatementUploadForm()

    return render(
        request,
        "onikisepet/import_upload.html",
        {"form": form, "format_error": error},
    )


def _draft_or_404(pk):
    return get_object_or_404(
        BankStatementImport.objects.select_related("account"), pk=pk
    )


@login_required
@permission_required(IMPORT_PERMISSIONS, raise_exception=True)
def import_preview(request, pk):
    """Review the parsed rows and choose categories before anything is posted."""
    statement_import = _draft_or_404(pk)
    message = None

    if request.method == "POST":
        categories, skipped = _read_row_choices(request, statement_import)
        bank_ops.apply_row_choices(
            statement_import, categories=categories, skipped=skipped
        )

        if request.POST.get("action") == "confirm":
            try:
                created = bank_ops.confirm_import(statement_import, request.user)
            except bank_ops.ImportNotReady as exc:
                message = str(exc)
            else:
                messages.success(
                    request,
                    _("Transactions imported: %(count)s")
                    % {"count": len(created)},
                )
                return redirect("import_list")

    rows = statement_import.rows.select_related("category", "transaction")

    return render(
        request,
        "onikisepet/import_preview.html",
        {
            "statement_import": statement_import,
            "rows": rows,
            "income_categories": Category.objects.filter(
                category_type=Category.CategoryType.INCOME, is_active=True
            ),
            "expense_categories": Category.objects.filter(
                category_type=Category.CategoryType.EXPENSE, is_active=True
            ),
            "blocking": bank_ops.rows_needing_attention(statement_import),
            "message": message,
        },
    )


def _read_row_choices(request, statement_import):
    """Pull per-row category and skip decisions out of the posted form."""
    categories, skipped = {}, set()
    valid_categories = {
        category.pk: category for category in Category.objects.all()
    }

    for row in statement_import.rows.all():
        if request.POST.get(f"skip_{row.pk}"):
            skipped.add(row.pk)

        raw = request.POST.get(f"category_{row.pk}", "").strip()
        if raw.isdigit():
            categories[row.pk] = valid_categories.get(int(raw))
        elif raw == "":
            categories[row.pk] = None

    return categories, skipped


@login_required
@permission_required(IMPORT_PERMISSIONS, raise_exception=True)
def import_cancel(request, pk):
    statement_import = _draft_or_404(pk)

    if request.method == "POST":
        # Already confirmed or cancelled: nothing to do, and the list
        # will show its current state anyway.
        with contextlib.suppress(bank_ops.ImportNotReady):
            bank_ops.cancel_import(statement_import)
        return redirect("import_list")

    return redirect("import_preview", pk=pk)


@login_required
@permission_required("onikisepet.view_transaction", raise_exception=True)
def import_sample_csv(request):
    """A correctly shaped example, so a first upload is less likely to fail."""
    response = HttpResponse(
        bank_ops.build_sample_csv(), content_type="text/csv; charset=utf-8"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{bank_ops.SAMPLE_FILENAME}"'
    )
    return response
