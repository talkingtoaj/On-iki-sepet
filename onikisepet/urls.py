from django.urls import path

from .views import (
    account_create,
    account_list,
    cash_expense_create,
    category_create,
    category_list,
    report_dashboard,
    transaction_create,
    transaction_list,
)

urlpatterns = [
    path("categories/", category_list, name="category_list"),
    path("categories/create/", category_create, name="category_create"),
    path("accounts/", account_list, name="account_list"),
    path("accounts/create/", account_create, name="account_create"),
    path("transactions/", transaction_list, name="transaction_list"),
    path("transactions/create/", transaction_create, name="transaction_create"),
    path(
        "cash-expenses/create/",
        cash_expense_create,
        name="cash_expense_create",
    ),
    path("reports/", report_dashboard, name="report_dashboard"),
]
