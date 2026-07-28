from pathlib import Path
from urllib.parse import urlencode

from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.forms import modelformset_factory
from django.http import (
    FileResponse,
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotFound,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET, require_POST

from onikisepet import messages as msg

from .decorators import application_access_required
from .form_guides import build_record_type_guide_context, get_form_guide
from .form_examples import build_transaction_form_example
from .form_currency import build_transaction_form_currency_context

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
    is_viewer,
)
from .selectors import (
    active_accounts,
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
    transaction_feedback,
)


def _create_transaction_from_form(form, user):
    transaction_data = form.get_transaction_data()
    transaction = Transaction(**transaction_data, created_by=user)
    approval.apply_initial_approval(transaction, user)
    transaction.save()
    audit.log_transaction_create(transaction=transaction, user=user)
    return transaction


def _render_transaction_create_form(request, *, form, guide_key, form_enctype=None):
    context = {
        "form": form,
        "form_guide": get_form_guide(guide_key),
        "form_example": build_transaction_form_example(form, guide_key),
        "form_currency": build_transaction_form_currency_context(form),
    }
    if form_enctype:
        context["form_enctype"] = form_enctype
    return render(request, "onikisepet/transaction_form.html", context)


def _flash_transaction_created(request, transaction):
    messages.success(
        request,
        transaction_feedback.transaction_created_message(transaction),
    )


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


def _transaction_list_filters(request):
    if request.method == "POST" and (
        "status" in request.POST or "mine" in request.POST
    ):
        source = request.POST
    else:
        source = request.GET
    status_filter = source.get("status", "")
    mine_filter = source.get("mine") == "1"
    return status_filter, mine_filter


def _transaction_list_url(*, status_filter="", mine_filter=False):
    params = {}
    if status_filter:
        params["status"] = status_filter
    if mine_filter:
        params["mine"] = "1"
    url = reverse("transaction_list")
    if params:
        return f"{url}?{urlencode(params)}"
    return url


def _build_transaction_list_context(request):
    transactions = _transaction_row_queryset().order_by("-date", "-pk")
    status_filter, mine_filter = _transaction_list_filters(request)
    if status_filter == "pending":
        transactions = transactions.filter(
            approval_status=Transaction.ApprovalStatus.PENDING,
        )
    elif status_filter == "approved":
        transactions = transactions.filter(
            approval_status=Transaction.ApprovalStatus.APPROVED,
        )
    elif status_filter == "rejected":
        transactions = transactions.filter(
            approval_status=Transaction.ApprovalStatus.REJECTED,
        )
    if mine_filter:
        transactions = transactions.filter(created_by=request.user)
    transactions = list(transactions)
    return {
        "transactions": transactions,
        "status_filter": status_filter,
        "mine_filter": mine_filter,
    }


def _category_bars(totals_by_category):
    sorted_items = sorted(
        totals_by_category,
        key=lambda item: item["total"],
        reverse=True,
    )
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
    income_category_bars = _category_bars(income_totals_by_category)
    expense_category_bars = _category_bars(expense_totals_by_category)
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
        "income_category_bars": income_category_bars,
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
    if is_viewer(request.user):
        return redirect("report_dashboard")

    context = dashboard.get_home_context(request.user)
    if can_approve_transactions(request.user):
        context.update(dashboard.get_approver_panel_context())
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
        form = CashExpenseForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            transaction = cash_ops.create_cash_transaction(form, request.user)
            _flash_transaction_created(request, transaction)
            return redirect("transaction_list")
    else:
        form = CashExpenseForm(user=request.user)

    return _render_transaction_create_form(
        request,
        form=form,
        guide_key="cash_expense",
        form_enctype="multipart/form-data",
    )


@application_access_required
def bank_expense_create(request):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden(msg.PERMISSION_CREATE_BANK_EXPENSES)

    if request.method == "POST":
        form = BankExpenseForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            transaction = bank_ops.create_bank_expense_transaction(form, request.user)
            _flash_transaction_created(request, transaction)
            return redirect("transaction_list")
    else:
        form = BankExpenseForm(user=request.user)

    return _render_transaction_create_form(
        request,
        form=form,
        guide_key="bank_expense",
        form_enctype="multipart/form-data",
    )


@application_access_required
def cash_income_create(request):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden(msg.PERMISSION_CREATE_CASH_INCOME)

    if request.method == "POST":
        form = CashIncomeForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = _create_transaction_from_form(form, request.user)
            _flash_transaction_created(request, transaction)
            return redirect("transaction_list")
    else:
        form = CashIncomeForm(user=request.user)

    return _render_transaction_create_form(
        request,
        form=form,
        guide_key="cash_income",
    )


@application_access_required
def online_donation_income_create(request):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden(msg.PERMISSION_CREATE_ONLINE_DONATION)

    if request.method == "POST":
        form = OnlineDonationIncomeForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = _create_transaction_from_form(form, request.user)
            _flash_transaction_created(request, transaction)
            return redirect("transaction_list")
    else:
        form = OnlineDonationIncomeForm(user=request.user)

    return _render_transaction_create_form(
        request,
        form=form,
        guide_key="online_donation",
    )


@application_access_required
def transfer_create(request):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden(msg.PERMISSION_CREATE_TRANSFERS)

    if request.method == "POST":
        form = TransferForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = _create_transaction_from_form(form, request.user)
            _flash_transaction_created(request, transaction)
            return redirect("transaction_list")
    else:
        form = TransferForm(user=request.user)

    return _render_transaction_create_form(
        request,
        form=form,
        guide_key="transfer",
    )


@application_access_required
def transaction_edit(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)

    if not can_edit_transaction(request.user, transaction):
        return HttpResponseForbidden(msg.PERMISSION_EDIT_TRANSACTIONS)

    if request.method == "POST":
        was_rejected = (
            transaction.approval_status == Transaction.ApprovalStatus.REJECTED
        )
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
            if was_rejected:
                approval.resubmit_transaction(updated, request.user)
                messages.success(request, msg.TRANSACTION_RESUBMITTED)
            else:
                messages.success(request, "İşlem güncellendi.")
            return redirect("transaction_list")
    else:
        form = TransactionEditForm(instance=transaction)

    return render(
        request,
        "onikisepet/transaction_edit_form.html",
        {
            "form": form,
            "transaction": transaction,
            "form_currency": build_transaction_form_currency_context(form),
        },
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
@require_POST
def transaction_bulk_approve(request):
    if not can_approve_transactions(request.user):
        return HttpResponseForbidden(msg.PERMISSION_APPROVE_TRANSACTIONS)

    raw_ids = request.POST.getlist("transaction_ids")
    transaction_ids = []
    for raw_id in raw_ids:
        try:
            transaction_ids.append(int(raw_id))
        except (TypeError, ValueError):
            continue

    approved_count = approval.bulk_approve_transactions(
        user=request.user,
        transaction_ids=transaction_ids,
    )

    status_filter, mine_filter = _transaction_list_filters(request)
    if approved_count:
        messages.success(request, msg.bulk_approve_success_message(approved_count))
    else:
        messages.warning(request, msg.BULK_APPROVE_NONE_SELECTED)

    if request.headers.get("HX-Request"):
        context = _build_transaction_list_context(request)
        return render(
            request,
            "onikisepet/partials/transaction_table.html",
            context,
        )

    return redirect(
        _transaction_list_url(
            status_filter=status_filter,
            mine_filter=mine_filter,
        )
    )


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

    form = BankStatementUploadForm()
    if request.method == "POST":
        form = BankStatementUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                bank_import = bank_import_ops.create_import_from_upload(
                    form.cleaned_data["file"],
                    request.user,
                    default_account=form.cleaned_data.get("default_account"),
                )
            except ValidationError as exc:
                for message in exc.messages:
                    form.add_error(None, message)
            else:
                messages.success(request, "Ekstre yüklendi.")
                return redirect("import_preview", pk=bank_import.pk)

    return render(
        request,
        "onikisepet/import_upload.html",
        {
            "form": form,
            "import_wizard_step": "upload",
            "upload_help_csv": msg.BANK_IMPORT_UPLOAD_HELP_CSV,
            "upload_help_pdf": msg.BANK_IMPORT_UPLOAD_HELP_PDF,
        },
    )


@application_access_required
@require_GET
def import_sample_csv(request):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden(msg.PERMISSION_IMPORT_BANK_STATEMENTS)

    sample_account = (
        active_accounts(account_type=Account.AccountType.BANK)
        .order_by("name")
        .first()
    )
    account_name = (
        sample_account.name
        if sample_account is not None
        else bank_import_ops.SAMPLE_CSV_ACCOUNT_FALLBACK
    )
    content = bank_import_ops.build_sample_csv_content(account_name=account_name)
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="{bank_import_ops.SAMPLE_CSV_FILENAME}"'
    )
    return response


IMPORT_PREVIEW_FILTERS = ("all", "pending", "ready", "error", "saved")


def _preview_filter_from_request(request):
    filter_name = request.GET.get("filter", "all")
    if filter_name not in IMPORT_PREVIEW_FILTERS:
        return "all"
    return filter_name


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
    all_rows = bank_import_ops.order_rows_for_preview(list(queryset))
    imported_rows = [row for row in all_rows if row.transaction_id]
    editable_rows = [row for row in all_rows if not row.transaction_id]
    ready_count = sum(
        1 for row in editable_rows if bank_import_ops.is_row_ready_to_import(row)
    )
    pending_count = bank_import_ops.count_pending_rows(all_rows)
    error_count = bank_import_ops.count_error_rows(all_rows)
    preview_filter = _preview_filter_from_request(request)

    preview_context = {
        "bank_import": bank_import,
        "imported_rows": imported_rows,
        "ready_count": ready_count,
        "pending_count": pending_count,
        "error_count": error_count,
        "imported_count": len(imported_rows),
        "preview_filter": preview_filter,
        "import_wizard_step": "preview",
    }

    if read_only:
        return render(
            request,
            "onikisepet/import_preview.html",
            {
                **preview_context,
                "rows": all_rows,
                "read_only": True,
            },
        )

    editable_ids = [row.pk for row in editable_rows]
    formset = BankStatementRowFormSet(
        queryset=queryset.filter(pk__in=editable_ids),
        data=request.POST or None,
    )
    if not request.POST:
        form_by_id = {form.instance.pk: form for form in formset}
        formset.forms = [
            form_by_id[row.pk]
            for row in editable_rows
            if row.pk in form_by_id
        ]

    if request.method == "POST" and formset.is_valid():
        formset.save()
        messages.success(request, "Sınıflandırma kaydedildi.")
        return redirect("import_confirm", pk=bank_import.pk)

    return render(
        request,
        "onikisepet/import_preview.html",
        {
            **preview_context,
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

    rows = list(
        bank_import.rows.select_related(
            "account",
            "category",
            "target_account",
            "transaction",
        ).order_by("row_number")
    )
    ready_rows = [row for row in rows if bank_import_ops.is_row_ready_to_import(row)]
    pending_count = bank_import_ops.count_pending_rows(rows)
    imported_count = sum(1 for row in rows if row.transaction_id)
    other_rows = [row for row in rows if row not in ready_rows]

    confirm_context = {
        "bank_import": bank_import,
        "rows": rows,
        "ready_rows": ready_rows,
        "other_rows": other_rows,
        "pending_count": pending_count,
        "imported_count": imported_count,
        "import_wizard_step": "confirm",
    }

    if request.method == "POST":
        if not can_confirm_bank_import(request.user):
            return HttpResponseForbidden(msg.PERMISSION_CONFIRM_BANK_IMPORT)

        try:
            result = bank_import_ops.confirm_import(bank_import, request.user)
        except ValidationError as exc:
            errors = list(exc.messages)
            messages.error(request, "Ekstre kaydedilemedi. Lütfen hataları kontrol edin.")

            return render(
                request,
                "onikisepet/import_confirm.html",
                {
                    **confirm_context,
                    "errors": errors,
                },
            )

        if result.pending_count:
            messages.success(
                request,
                msg.bank_import_partial_success_message(
                    result.imported_count,
                    result.pending_count,
                ),
            )
            return redirect("import_preview", pk=bank_import.pk)

        messages.success(
            request,
            msg.bank_import_full_success_message(result.imported_count),
        )
        return redirect("transaction_list")

    return render(
        request,
        "onikisepet/import_confirm.html",
        {
            **confirm_context,
            "errors": [],
        },
    )


@application_access_required
def finance_guide(request):
    return render(request, "onikisepet/finance_guide.html")


@application_access_required
def record_type_guide(request):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden(msg.PERMISSION_VIEW_RECORD_GUIDE)

    return render(
        request,
        "onikisepet/record_type_guide.html",
        {"record_type_guide": build_record_type_guide_context()},
    )


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
