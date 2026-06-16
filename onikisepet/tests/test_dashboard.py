from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from onikisepet.usecases import dashboard

from .helpers import TransactionTestMixin


class DashboardUseCaseTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.admin_user = self.create_user("dashboard_admin", is_superuser=True)
        self.income_category = self.create_category(
            name="Bağış",
            category_type="income",
        )
        self.expense_category = self.create_category(
            name="Kira",
            category_type="expense",
        )
        self.cash_account = self.create_account(
            name="Kasa",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
            opening_balance=Decimal("1000.00"),
        )

    def test_get_dashboard_context_includes_monthly_net(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("500.00"),
            target_account=self.cash_account,
            category=self.income_category,
            date="2026-06-10",
            created_by=self.admin_user,
        )
        self.create_transaction(
            transaction_type="expense",
            amount=Decimal("200.00"),
            source_account=self.cash_account,
            category=self.expense_category,
            date="2026-06-12",
            created_by=self.admin_user,
        )

        context = dashboard.get_dashboard_context(reference_date=date(2026, 6, 15))

        self.assertEqual(context["currency_summary"]["TRY"]["total_income"], Decimal("500.00"))
        self.assertEqual(context["currency_summary"]["TRY"]["total_expenses"], Decimal("200.00"))
        self.assertEqual(context["currency_summary"]["TRY"]["net_financial_status"], Decimal("300.00"))

    def test_get_dashboard_context_includes_top_expenses(self):
        self.create_transaction(
            transaction_type="expense",
            amount=Decimal("500.00"),
            source_account=self.cash_account,
            category=self.expense_category,
            date="2026-06-10",
            created_by=self.admin_user,
        )

        context = dashboard.get_dashboard_context(reference_date=date(2026, 6, 15))

        self.assertEqual(len(context["top_expenses"]), 1)
        self.assertEqual(context["top_expenses"][0]["category"], self.expense_category)

    def test_get_dashboard_context_includes_account_balances(self):
        context = dashboard.get_dashboard_context(reference_date=date(2026, 6, 15))

        self.assertEqual(len(context["account_balances"]), 1)
        self.assertEqual(context["account_balances"][0]["balance"], Decimal("1000.00"))


class HomeDashboardViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.home_url = reverse("home")
        self.viewer_user = self.create_user("home_viewer", group_name="Viewer")

    def test_home_displays_dashboard_sections(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Finans Özeti")
        self.assertContains(response, "Hesap Bakiyeleri")
        self.assertContains(response, "En Büyük Gider Kalemleri")
