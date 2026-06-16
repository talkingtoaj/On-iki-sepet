from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date

from .forms import (
    AccountForm,
    BankExpenseForm,
    CashExpenseForm,
    CashIncomeForm,
    CategoryForm,
    OnlineDonationIncomeForm,
    TransactionEditForm,
    TransferForm,
    TransactionForm,
)
from .models import Account, Category, Receipt, Transaction
from .permissions import (
    can_create_transactions,
    can_manage_accounts,
    can_manage_categories,
)
from .usecases import audit, cash_ops, dashboard, financial_calculations, report_periods


def _create_transaction_from_form(form, user):
    transaction_data = form.get_transaction_data()
    return Transaction.objects.create(
        **transaction_data,
        created_by=user,
    )


@login_required
def home(request):
    context = dashboard.get_dashboard_context()
    return render(request, "onikisepet/home.html", context)


@login_required
def category_list(request):
    categories = Category.objects.all()
    return render(
        request,
        "onikisepet/category_list.html",
        {"categories": categories},
    )


@login_required
def category_create(request):
    if not can_manage_categories(request.user):
        return HttpResponseForbidden("You do not have permission to create categories.")

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
def account_list(request):
    accounts = Account.objects.all()
    return render(
        request,
        "onikisepet/account_list.html",
        {"accounts": accounts},
    )


@login_required
def account_create(request):
    if not can_manage_accounts(request.user):
        return HttpResponseForbidden("You do not have permission to create accounts.")

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
def transaction_list(request):
    transactions = (
        Transaction.objects.select_related(
            "source_account",
            "target_account",
            "category",
        )
        .prefetch_related("receipts")
        .order_by("-date", "-pk")
    )
    return render(
        request,
        "onikisepet/transaction_list.html",
        {"transactions": transactions},
    )


@login_required
def transaction_create(request):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden(
            "You do not have permission to create transactions."
        )

    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.created_by = request.user
            transaction.save()
            return redirect("transaction_list")
    else:
        form = TransactionForm()

    return render(
        request,
        "onikisepet/transaction_form.html",
        {"form": form},
    )


@login_required
def cash_expense_create(request):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden(
            "You do not have permission to create cash expenses."
        )

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
def bank_expense_create(request):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden(
            "You do not have permission to create bank expenses."
        )

    if request.method == "POST":
        form = BankExpenseForm(request.POST)
        if form.is_valid():
            _create_transaction_from_form(form, request.user)
            return redirect("transaction_list")
    else:
        form = BankExpenseForm()

    return render(
        request,
        "onikisepet/bank_expense_form.html",
        {"form": form},
    )


@login_required
def cash_income_create(request):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden(
            "Nakit gelir oluşturma yetkiniz yok."
        )

    if request.method == "POST":
        form = CashIncomeForm(request.POST)
        if form.is_valid():
            _create_transaction_from_form(form, request.user)
            return redirect("transaction_list")
    else:
        form = CashIncomeForm()

    return render(
        request,
        "onikisepet/cash_income_form.html",
        {"form": form},
    )


@login_required
def online_donation_income_create(request):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden(
            "You do not have permission to create online donation income."
        )

    if request.method == "POST":
        form = OnlineDonationIncomeForm(request.POST)
        if form.is_valid():
            _create_transaction_from_form(form, request.user)
            return redirect("transaction_list")
    else:
        form = OnlineDonationIncomeForm()

    return render(
        request,
        "onikisepet/online_donation_income_form.html",
        {"form": form},
    )


@login_required
def transfer_create(request):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden(
            "You do not have permission to create transfers."
        )

    if request.method == "POST":
        form = TransferForm(request.POST)
        if form.is_valid():
            _create_transaction_from_form(form, request.user)
            return redirect("transaction_list")
    else:
        form = TransferForm()

    return render(
        request,
        "onikisepet/transfer_form.html",
        {"form": form},
    )


@login_required
def transaction_edit(request, pk):
    if not can_create_transactions(request.user):
        return HttpResponseForbidden("İşlem düzenleme yetkiniz yok.")

    transaction = get_object_or_404(Transaction, pk=pk)

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
            return redirect("transaction_list")
    else:
        form = TransactionEditForm(instance=transaction)

    return render(
        request,
        "onikisepet/transaction_edit_form.html",
        {"form": form, "transaction": transaction},
    )


@login_required
def receipt_download(request, pk):
    receipt = get_object_or_404(Receipt, pk=pk)
    receipt.file.open("rb")
    filename = receipt.original_filename or Path(receipt.file.name).name

    return FileResponse(
        receipt.file,
        as_attachment=False,
        filename=filename,
    )


@login_required
def report_dashboard(request):
    transactions = Transaction.objects.all()
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
    total_income = financial_calculations.calculate_income_total(transactions)
    total_expenses = financial_calculations.calculate_expense_total(transactions)
    currency_summary = financial_calculations.build_currency_summary(transactions)
    transfer_summary = financial_calculations.build_transfer_summary(transactions)
    income_totals_by_category = (
        financial_calculations.calculate_income_totals_by_category(transactions)
    )
    expense_totals_by_category = (
        financial_calculations.calculate_expense_totals_by_category(transactions)
    )
    account_balances = [
        {
            "account": account,
            "balance": (
                financial_calculations.calculate_account_balance_for_transactions(
                    account,
                    transactions,
                )
            ),
        }
        for account in accounts
    ]

    return render(
        request,
        "onikisepet/report_dashboard.html",
        {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_financial_status": total_income - total_expenses,
            "currency_summary": currency_summary,
            "transfer_summary": transfer_summary,
            "income_totals_by_category": income_totals_by_category,
            "expense_totals_by_category": expense_totals_by_category,
            "account_balances": account_balances,
            "start_date": start_date,
            "end_date": end_date,
            "start_date_value": start_date_value,
            "end_date_value": end_date_value,
            "active_period": active_period,
        },
    )
