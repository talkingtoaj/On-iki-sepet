from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from .forms import AccountForm, CashExpenseForm, CategoryForm, TransactionForm
from .models import Account, Category, Receipt, Transaction
from .usecases import financial_calculations
from .usecases import cash_ops

def _can_manage_categories(user):
    return user.is_superuser


def _can_manage_accounts(user):
    return user.is_superuser


def _can_create_transactions(user):
    return user.is_superuser or user.groups.filter(name="Data Entry").exists()


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
    if not _can_manage_categories(request.user):
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
    if not _can_manage_accounts(request.user):
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
    transactions = Transaction.objects.all()
    return render(
        request,
        "onikisepet/transaction_list.html",
        {"transactions": transactions},
    )


@login_required
def transaction_create(request):
    if not _can_create_transactions(request.user):
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
    if not _can_create_transactions(request.user):
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
def report_dashboard(request):
    transactions = Transaction.objects.all()
    accounts = Account.objects.all()
    total_income = financial_calculations.calculate_income_total(transactions)
    total_expenses = financial_calculations.calculate_expense_total(transactions)
    account_balances = [
        {
            "account": account,
            "balance": financial_calculations.calculate_account_balance(account),
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
            "account_balances": account_balances,
        },
    )
