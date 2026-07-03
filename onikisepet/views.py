from pathlib import Path

from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.forms import modelformset_factory
from django.http import FileResponse, HttpResponseForbidden, HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET, require_POST

from onikisepet import messages as msg

from .decorators import application_access_required

from .forms import (
    AccountForm,
    AccountChangeRequestForm,
    AccountChangeRequestRejectForm,
    BankExpenseForm,
    BankStatementRowClassificationForm,
    BankStatementUploadForm,
    CashExpenseForm,
    CashIncomeForm,
    CategoryForm,
    OnlineDonationIncomeForm,
    TransactionEditForm,
    TransactionRejectForm,
    TransferForm,
)
from .models import (
    Account,
    AccountChangeRequest,
    BankStatementImport,
    BankStatementRow,
    Category,
    Receipt,
    Transaction,
)
from .permissions import (
    can_approve_transactions,
    can_confirm_bank_import,
    can_create_transactions,
    can_edit_bank_import_preview,
    can_edit_transaction,
    can_manage_accounts,
    can_manage_categories,
    can_request_account_changes,
    can_view_pending_account_change_requests,
    can_view_pending_bank_imports,
    can_view_reference_data,
    can_view_operational_pages,
    can_view_transaction_list,
)
from .selectors import (
    approved_transactions,
    pending_account_change_requests,
    pending_bank_imports,
    pending_transactions,
)
from .usecases import (
    account_changes,
    audit,
    approval,
    bank_import as bank_import_ops,
    bank_ops,
    cash_ops,
    dashboard,
    financial_calculations,
    report_periods,
)


def _create_transaction_from_form(form, user):
    transaction_data = form.get_transaction_data()
    transaction = Transaction(**transaction_data, created_by=user)
    approval.apply_initial_approval(transaction, user)
    transaction.save()
    audit.log_transaction_create(transaction=transaction, user=user)
    return transaction


BankStatementRowFormSet = modelformset_factory(
    BankStatementRow,
    form=BankStatementRowClassificationForm,
    extra=0,
    can_delete=False,
)

SUPPORTED_CURRENCY_CODES = ("TRY", "USD", "EUR")
FINANCE_REFRESH_CACHE_KEY = "kut:finance_last_refresh"


def _transaction_row_queryset():
    return (
        Transaction.objects.select_related(
            "source_account",
            "target_account",
            "category",
            "created_by",
            "approved_by",
        )
        .prefetch_related("receipts")
    )


def _render_transaction_row(request, transaction):
    transaction = _transaction_row_queryset().get(pk=transaction.pk)
    return render(
        request,
        "onikisepet/partials/transaction_row.html",
        {
            "transaction": transaction,
        },
    )


def _build_transaction_list_context(request):
    transactions = _transaction_row_queryset().order_by("-date", "-pk")
    status_filter = request.GET.get("status", "")
    if status_filter == "pending":
        transactions = transactions.filter(
            approval_status=Transaction.ApprovalStatus.PENDING,
        )
    elif status_filter == "approved":
        transactions = transactions.filter(
            approval_status=Transaction.ApprovalStatus.APPROVED,
        )
    transactions = list(transactions)
    return {
        "transactions": transactions,
        "status_filter": status_filter,
    }


def _top_expense_category_bars(expense_totals_by_category, limit=5):
    sorted_items = sorted(
        expense_totals_by_category,
        key=lambda item: item["total"],
        reverse=True,
    )[:limit]
    if not sorted_items:
        return []

    max_total = sorted_items[0]["total"]
    bars = []
    for item in sorted_items:
        if max_total > 0:
            bar_percent = float((item["total"] / max_total) * 100)
        else:
            bar_percent = 0.0
        bars.append({**item, "bar_percent": round(bar_percent, 1)})
    return bars


def _build_report_context(request):
    transactions = Transaction.objects.filter(
        approval_status=Transaction.ApprovalStatus.APPROVED,
    )
    period_value = request.GET.get("period", "")
    start_date_value = request.GET.get("start_date", "")
    end_date_value = request.GET.get("end_date", "")

    preset_start, preset_end, active_period = report_periods.resolve_report_period(
        period_value
    )
    if preset_start is not None and preset_end is not None:
        start_date = preset_start
        end_date = preset_end
        start_date_value = start_date.isoformat()
        end_date_value = end_date.isoformat()
    else:
        start_date = parse_date(start_date_value) if start_date_value else None
        end_date = parse_date(end_date_value) if end_date_value else None

    if start_date is not None:
        transactions = transactions.filter(date__gte=start_date)
    if end_date is not None:
        transactions = transactions.filter(date__lte=end_date)

    accounts = Account.objects.all()
    currency_summary = financial_calculations.build_currency_summary(transactions)
    transfer_summary = financial_calculations.build_transfer_summary(transactions)
    transfer_report = financial_calculations.build_transfer_report(transactions)
    income_totals_by_category = (
        financial_calculations.calculate_income_totals_by_category(transactions)
    )
    expense_totals_by_category = (
        financial_calculations.calculate_expense_totals_by_category(transactions)
    )
    expense_category_bars = _top_expense_category_bars(expense_totals_by_category)
    account_balances = [
        {
            "account": account,
            "balance": financial_calculations.calculate_account_balance(account),
        }
        for account in accounts
    ]

    return {
        "currency_summary": currency_summary,
        "transfer_summary": transfer_summary,
        "transfer_report": transfer_report,
        "income_totals_by_category": income_totals_by_category,
        "expense_totals_by_category": expense_totals_by_category,
        "expense_category_bars": expense_category_bars,
        "account_balances": account_balances,
        "start_date": start_date,
        "end_date": end_date,
        "start_date_value": start_date_value,
        "end_date_value": end_date_value,
        "active_period": active_period,
        "active_period_label": report_periods.get_period_label(active_period),
    }


def _get_bank_import_for_user(request, pk, *, allow_approver_access=False):
    bank_import = get_object_or_404(BankStatementImport, pk=pk)
    if request.user.is_superuser:
        return bank_import, None
    if allow_approver_access and can_approve_transactions(request.user):
        return bank_import, None
    if bank_import.uploaded_by_id != request.user.id:
        return None, HttpResponseForbidden(msg.PERMISSION_IMPORT_BANK_STATEMENTS)
    return bank_import, None


@application_access_required
def home(request):
    context = dashboard.get_dashboard_context()
    return render(request, "onikisepet/home.html", context)


@application_access_required
def category_list(request):
    if not can_view_reference_data(request.user):
        return HttpResponseForbidden(msg.PERMISSION_VIEW_OPERATIONAL_PAGES)

    categories = Category.objects.all()
    return render(
        request,
        "onikisepet/category_list.html",
        {"categories": categories},
    )


@application_access_required
def category_create(request):
    if not can_manage_categories(request.user):
        return HttpResponseForbidden(msg.PERMISSION_CREATE_CATEGORIES)

    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Kategori oluşturuldu.")
            return redirect("category_list")
    else:
        form = CategoryForm()

    return render(
        request,
        "onikisepet/category_form.html",
        {"form": form},
    )


@application_access_required
def account_list(request):
    if not can_view_reference_data(request.user):
        return HttpResponseForbidden(msg.PERMISSION_VIEW_OPERATIONAL_PAGES)

    accounts = Account.objects.all()
    account_balances = [
        {
            "account": account,
            "balance": financial_calculations.calculate_account_balance(account),
        }
        for account in accounts
    ]
    return render(
        request,
        "onikisepet/account_list.html",
        {"account_balances": account_balances},
    )


@application_access_required
def account_create(request):
    if not can_manage_accounts(request.user):
        return HttpResponseForbidden(msg.PERMISSION_CREATE_ACCOUNTS)

    if request.method == "POST":
        form = AccountForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Hesap oluşturuldu.")
            return redirect("account_list")
    else:
        form = AccountForm()

    return render(
        request,
        "onikisepet/account_form.html",
        {"form": form},
    )


@application_access_required
def account_change_request(request, pk):
    if not can_request_account_changes(request.user):
        return HttpResponseForbidden(msg.PERMISSION_REQUEST_ACCOUNT_CHANGES)

    account = get_object_or_404(Account, pk=pk)

    if request.method == "POST":
        form = AccountChangeRequestForm(request.POST)
        if form.is_valid():
            AccountChangeRequest.objects.create(
                account=account,
                requested_by=request.user,
                proposed_name=form.cleaned_data["proposed_name"],
            )
            messages.success(request, "Hesap değişikliği talebi gönderildi.")
            return redirect("account_list")
    else:
        form = AccountChangeRequestForm(initial={"proposed_name": account.name})

    return render(
        request,
        "onikisepet/account_change_request_form.html",
        {"form": form, "account": account},
    )


@application_access_required
def account_change_request_approve(request, pk):
    if not can_approve_transactions(request.user):
        return HttpResponseForbidden(msg.PERMISSION_APPROVE_TRANSACTIONS)

    change_request = get_object_or_404(AccountChangeRequest, pk=pk)
    if change_request.status != AccountChangeRequest.Status.PENDING:
        return redirect("account_change_request_list")

    if request.method == "POST":
        account_changes.approve_change_request(change_request, request.user)
        messages.success(request, "Hesap değişikliği onaylandı.")

    return redirect("account_change_request_list")


@application_access_required
def account_change_request_list(request):
    if not can_view_pending_account_change_requests(request.user):
        return HttpResponseForbidden(msg.PERMISSION_APPROVE_TRANSACTIONS)

    return render(
        request,
        "onikisepet/account_change_request_list.html",
        {"change_requests": pending_account_change_requests()},
    )


@application_access_required
def account_change_request_reject(request, pk):
    if not can_approve_transactions(request.user):
        return HttpResponseForbidden(msg.PERMISSION_APPROVE_TRANSACTIONS)

    change_request = get_object_or_404(AccountChangeRequest, pk=pk)
    if change_request.status != AccountChangeRequest.Status.PENDING:
        return redirect("account_change_request_list")

    if request.method == "POST":
        form = AccountChangeRequestRejectForm(request.POST)
        if form.is_valid():
            account_changes.reject_change_request(
                change_request,
                request.user,
                form.cleaned_data["rejection_reason"],
            )
            messages.success(request, "Hesap değişikliği reddedildi.")
            return redirect("account_change_request_list")
    else:
        form = AccountChangeRequestRejectForm()

    return render(
        request,
        "onikisepet/account_change_request_reject_form.html",
        {"form": form, "change_request": change_request},
    )


@application_access_required
def transaction_list(request):
    if not can_view_transaction_list(request.user):
        return HttpResponseForbidden(msg.PERMISSION_VIEW_OPERATIONAL_PAGES)

    context = _build_transaction_list_context(request)
    return render(
        request,
        "onikisepet/transaction_list.html",
        context,
    )


@application_access_required
def htmx_transaction_list(request):
    if not can_view_transaction_list(request.user):
        return HttpResponseForbidden(msg.PERMISSION_VIEW_OPERATIONAL_PAGES)

    context = _build_transaction_list_context(request)
    return render(
        request,
        "onikisepet/partials/transaction_table.html",
        context,
    )


@application_access_required
def cash_expense_create(request):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden(msg.PERMISSION_CREATE_CASH_EXPENSES)

    if request.method == "POST":
        form = CashExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            cash_ops.create_cash_transaction(form, request.user)
            messages.success(request, "Nakit gider kaydedildi.")
            return redirect("transaction_list")
    else:
        form = CashExpenseForm()

    return render(
        request,
        "onikisepet/cash_expense_form.html",
        {"form": form},
    )


@application_access_required
def bank_expense_create(request):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden(msg.PERMISSION_CREATE_BANK_EXPENSES)

    if request.method == "POST":
        form = BankExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            bank_ops.create_bank_expense_transaction(form, request.user)
            messages.success(request, "Banka gideri kaydedildi.")
            return redirect("transaction_list")
    else:
        form = BankExpenseForm()

    return render(
        request,
        "onikisepet/bank_expense_form.html",
        {"form": form},
    )


@application_access_required
def cash_income_create(request):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden(msg.PERMISSION_CREATE_CASH_INCOME)

    if request.method == "POST":
        form = CashIncomeForm(request.POST)
        if form.is_valid():
            _create_transaction_from_form(form, request.user)
            messages.success(request, "Nakit gelir kaydedildi.")
            return redirect("transaction_list")
    else:
        form = CashIncomeForm()

    return render(
        request,
        "onikisepet/cash_income_form.html",
        {"form": form},
    )


@application_access_required
def online_donation_income_create(request):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden(msg.PERMISSION_CREATE_ONLINE_DONATION)

    if request.method == "POST":
        form = OnlineDonationIncomeForm(request.POST)
        if form.is_valid():
            _create_transaction_from_form(form, request.user)
            messages.success(request, "Online bağış kaydedildi.")
            return redirect("transaction_list")
    else:
        form = OnlineDonationIncomeForm()

    return render(
        request,
        "onikisepet/online_donation_income_form.html",
        {"form": form},
    )


@application_access_required
def transfer_create(request):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden(msg.PERMISSION_CREATE_TRANSFERS)

    if request.method == "POST":
        form = TransferForm(request.POST)
        if form.is_valid():
            _create_transaction_from_form(form, request.user)
            messages.success(request, "Transfer kaydedildi.")
            return redirect("transaction_list")
    else:
        form = TransferForm()

    return render(
        request,
        "onikisepet/transfer_form.html",
        {"form": form},
    )


@application_access_required
def transaction_edit(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)

    if not can_edit_transaction(request.user, transaction):
        return HttpResponseForbidden(msg.PERMISSION_EDIT_TRANSACTIONS)

    if request.method == "POST":
        before = audit.snapshot_transaction(transaction)
        form = TransactionEditForm(request.POST, instance=transaction)
        if form.is_valid():
            updated = form.save()
            after = audit.snapshot_transaction(updated)
            audit.log_transaction_update(
                transaction=updated,
                user=request.user,
                before=before,
                after=after,
            )
            messages.success(request, "İşlem güncellendi.")
            return redirect("transaction_list")
    else:
        form = TransactionEditForm(instance=transaction)

    return render(
        request,
        "onikisepet/transaction_edit_form.html",
        {"form": form, "transaction": transaction},
    )


@application_access_required
def transaction_approve(request, pk):
    if not can_approve_transactions(request.user):
        return HttpResponseForbidden(msg.PERMISSION_APPROVE_TRANSACTIONS)

    transaction = get_object_or_404(Transaction, pk=pk)
    if transaction.approval_status != Transaction.ApprovalStatus.PENDING:
        return redirect("transaction_list")

    if request.method == "POST":
        approval.approve_transaction(transaction, request.user)
        if request.headers.get("HX-Request"):
            return _render_transaction_row(request, transaction)
        messages.success(request, "İşlem onaylandı.")

    return redirect("transaction_list")


@application_access_required
def transaction_reject(request, pk):
    if not can_approve_transactions(request.user):
        return HttpResponseForbidden(msg.PERMISSION_APPROVE_TRANSACTIONS)

    transaction = get_object_or_404(Transaction, pk=pk)
    if transaction.approval_status != Transaction.ApprovalStatus.PENDING:
        return redirect("transaction_list")

    if request.method == "POST":
        form = TransactionRejectForm(request.POST)
        if form.is_valid():
            approval.reject_transaction(
                transaction,
                request.user,
                rejection_reason=form.cleaned_data["rejection_reason"],
            )
            if request.headers.get("HX-Request"):
                return _render_transaction_row(request, transaction)
            messages.success(request, "İşlem reddedildi.")
            return redirect("transaction_list")
        if request.headers.get("HX-Request"):
            return render(
                request,
                "onikisepet/partials/transaction_reject_form.html",
                {"form": form, "transaction": transaction},
            )
    else:
        form = TransactionRejectForm()
        if request.headers.get("HX-Request"):
            return render(
                request,
                "onikisepet/partials/transaction_reject_form.html",
                {"form": form, "transaction": transaction},
            )

    return render(
        request,
        "onikisepet/transaction_reject_form.html",
        {"form": form, "transaction": transaction},
    )


@application_access_required
def receipt_download(request, pk):
    if not can_view_operational_pages(request.user):
        return HttpResponseForbidden(msg.PERMISSION_VIEW_OPERATIONAL_PAGES)

    receipt = get_object_or_404(Receipt, pk=pk)
    receipt.file.open("rb")
    filename = receipt.original_filename or Path(receipt.file.name).name

    return FileResponse(
        receipt.file,
        as_attachment=False,
        filename=filename,
    )


def _render_report_response(request, *, force_partial=False):
    context = _build_report_context(request)
    if force_partial or request.headers.get("HX-Request"):
        context["is_htmx"] = True
        return render(
            request,
            "onikisepet/partials/report_summary.html",
            context,
        )
    return render(
        request,
        "onikisepet/report_dashboard.html",
        context,
    )


@application_access_required
def report_dashboard(request):
    return _render_report_response(request)


@application_access_required
def htmx_report_summary(request):
    return _render_report_response(request, force_partial=True)


@application_access_required
def import_list(request):
    if not can_view_pending_bank_imports(request.user):
        return HttpResponseForbidden(msg.PERMISSION_CONFIRM_BANK_IMPORT)

    return render(
        request,
        "onikisepet/import_list.html",
        {"bank_imports": pending_bank_imports()},
    )


@application_access_required
def import_new(request):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden(msg.PERMISSION_IMPORT_BANK_STATEMENTS)

    if request.method == "POST":
        form = BankStatementUploadForm(request.POST, request.FILES)
        if form.is_valid():
            bank_import = bank_import_ops.create_import_from_upload(
                form.cleaned_data["file"],
                request.user,
                default_account=form.cleaned_data.get("default_account"),
            )
            messages.success(request, "Ekstre yüklendi.")
            return redirect("import_preview", pk=bank_import.pk)
    else:
        form = BankStatementUploadForm()

    return render(
        request,
        "onikisepet/import_upload.html",
        {"form": form},
    )


@application_access_required
def import_preview(request, pk):
    approver_access = can_confirm_bank_import(request.user)
    if not can_create_transactions(request.user) and not approver_access:
        return HttpResponseForbidden(msg.PERMISSION_IMPORT_BANK_STATEMENTS)

    bank_import, forbidden_response = _get_bank_import_for_user(
        request,
        pk,
        allow_approver_access=approver_access,
    )
    if forbidden_response is not None:
        return forbidden_response

    if bank_import.status == BankStatementImport.Status.CONFIRMED:
        return redirect("transaction_list")

    queryset = bank_import.rows.select_related("account", "category", "target_account")
    read_only = not can_edit_bank_import_preview(request.user, bank_import)

    if read_only:
        return render(
            request,
            "onikisepet/import_preview.html",
            {
                "bank_import": bank_import,
                "rows": queryset.order_by("row_number"),
                "read_only": True,
            },
        )

    formset = BankStatementRowFormSet(
        queryset=queryset,
        data=request.POST or None,
    )

    if request.method == "POST" and formset.is_valid():
        formset.save()
        messages.success(request, "Sınıflandırma kaydedildi.")
        return redirect("import_confirm", pk=bank_import.pk)

    return render(
        request,
        "onikisepet/import_preview.html",
        {
            "bank_import": bank_import,
            "formset": formset,
            "read_only": False,
        },
    )


@application_access_required
def import_confirm(request, pk):
    bank_import, forbidden_response = _get_bank_import_for_user(
        request,
        pk,
        allow_approver_access=True,
    )
    if forbidden_response is not None:
        return forbidden_response

    if bank_import.status == BankStatementImport.Status.CONFIRMED:
        return redirect("transaction_list")

    rows = bank_import.rows.select_related(
        "account",
        "category",
        "target_account",
    ).order_by("row_number")
    importable_rows = [row for row in rows if not row.is_skipped and not row.parse_error]

    if request.method == "POST":
        if not can_confirm_bank_import(request.user):
            return HttpResponseForbidden(msg.PERMISSION_CONFIRM_BANK_IMPORT)

        try:
            bank_import_ops.confirm_import(bank_import, request.user)
        except ValidationError as exc:
            errors = list(exc.messages)
            messages.error(request, "Ekstre kaydedilemedi. Lütfen hataları kontrol edin.")

            return render(
                request,
                "onikisepet/import_confirm.html",
                {
                    "bank_import": bank_import,
                    "rows": rows,
                    "importable_rows": importable_rows,
                    "errors": errors,
                },
            )

        messages.success(request, "İşlemler içe aktarıldı.")
        return redirect("transaction_list")

    return render(
        request,
        "onikisepet/import_confirm.html",
        {
            "bank_import": bank_import,
            "rows": rows,
            "importable_rows": importable_rows,
            "errors": [],
        },
    )


@application_access_required
def finance_guide(request):
    return render(request, "onikisepet/finance_guide.html")


@application_access_required
def htmx_finance_income(request):
    return render(
        request,
        "onikisepet/partials/finance_income_overview.html",
        dashboard.get_dashboard_context(),
    )


@application_access_required
def htmx_finance_expenses(request):
    return render(
        request,
        "onikisepet/partials/finance_expense_overview.html",
        dashboard.get_dashboard_context(),
    )


@application_access_required
def htmx_finance_accounts(request):
    return render(
        request,
        "onikisepet/partials/finance_accounts_overview.html",
        dashboard.get_dashboard_context(),
    )


def _htmx_currency_context(currency):
    context = dashboard.get_dashboard_context()
    return {
        "currency": currency,
        "summary": context["currency_summary"][currency],
        "accounts": [
            item
            for item in context["account_balances"]
            if item["account"].currency == currency
        ],
        "month_start": context["month_start"],
        "month_end": context["month_end"],
    }


@application_access_required
def htmx_currency_detail(request, currency):
    currency = currency.upper()
    if currency not in SUPPORTED_CURRENCY_CODES:
        return HttpResponseNotFound()
    return render(
        request,
        "onikisepet/partials/currency_detail.html",
        _htmx_currency_context(currency),
    )


def _finance_stats_payload(user):
    data = {
        "approved_transactions": approved_transactions().count(),
        "active_accounts": Account.objects.filter(is_active=True).count(),
        "pending_approvals": None,
        "last_refreshed_at": cache.get(FINANCE_REFRESH_CACHE_KEY),
    }
    if can_approve_transactions(user):
        data["pending_approvals"] = pending_transactions().count()
    return data


@application_access_required
@require_GET
def api_finance_stats(request):
    return JsonResponse(
        {
            "ok": True,
            "data": _finance_stats_payload(request.user),
        }
    )


@application_access_required
@require_POST
def api_finance_refresh(request):
    now = timezone.now().isoformat()
    cache.set(FINANCE_REFRESH_CACHE_KEY, now, timeout=None)
    payload = _finance_stats_payload(request.user)
    payload["last_refreshed_at"] = now
    return JsonResponse({"ok": True, "data": payload})
