from django.urls import path

from .views import (
    account_create,
    account_list,
    cash_expense_create,
    category_create,
    category_list,
    exchange_rate_create,
    exchange_rate_list,
    report_dashboard,
    transaction_create,
    transaction_detail,
    transaction_edit,
    transaction_list,
    transaction_void,
)

urlpatterns = [
    path("", report_dashboard, name="home"),
    path("categories/", category_list, name="category_list"),
    path("categories/create/", category_create, name="category_create"),
    path("accounts/", account_list, name="account_list"),
    path("accounts/create/", account_create, name="account_create"),
    path("transactions/", transaction_list, name="transaction_list"),
    path("transactions/create/", transaction_create, name="transaction_create"),
    path(
        "transactions/<int:pk>/",
        transaction_detail,
        name="transaction_detail",
    ),
    path(
        "transactions/<int:pk>/edit/",
        transaction_edit,
        name="transaction_edit",
    ),
    path(
        "transactions/<int:pk>/void/",
        transaction_void,
        name="transaction_void",
    ),
    path(
        "cash-expenses/create/",
        cash_expense_create,
        name="cash_expense_create",
    ),
    path("exchange-rates/", exchange_rate_list, name="exchange_rate_list"),
    path(
        "exchange-rates/create/",
        exchange_rate_create,
        name="exchange_rate_create",
    ),
    path("reports/", report_dashboard, name="report_dashboard"),
]
