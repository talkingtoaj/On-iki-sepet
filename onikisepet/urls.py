from django.urls import path

from .views import (
    account_create,
    account_list,
    bank_expense_create,
    cash_expense_create,
    cash_income_create,
    category_create,
    category_list,
    home,
    online_donation_income_create,
    receipt_download,
    report_dashboard,
    transfer_create,
    transaction_create,
    transaction_edit,
    transaction_list,
)

urlpatterns = [
    path("", home, name="home"),
    path("categories/", category_list, name="category_list"),
    path("categories/create/", category_create, name="category_create"),
    path("accounts/", account_list, name="account_list"),
    path("accounts/create/", account_create, name="account_create"),
    path("transactions/", transaction_list, name="transaction_list"),
    path("transactions/<int:pk>/edit/", transaction_edit, name="transaction_edit"),
    path("transactions/create/", transaction_create, name="transaction_create"),
    path(
        "cash-incomes/create/",
        cash_income_create,
        name="cash_income_create",
    ),
    path(
        "cash-expenses/create/",
        cash_expense_create,
        name="cash_expense_create",
    ),
    path(
        "bank-expenses/create/",
        bank_expense_create,
        name="bank_expense_create",
    ),
    path(
        "online-donations/create/",
        online_donation_income_create,
        name="online_donation_income_create",
    ),
    path(
        "transfers/create/",
        transfer_create,
        name="transfer_create",
    ),
    path(
        "receipts/<int:pk>/download/",
        receipt_download,
        name="receipt_download",
    ),
    path("reports/", report_dashboard, name="report_dashboard"),
]
