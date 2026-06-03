from decimal import Decimal

from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse

from .helpers import TransactionTestMixin


class ReportDashboardViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.report_dashboard_url = reverse("report_dashboard")

        self.admin_user = self.create_user("report_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "report_data_entry",
            group_name="Data Entry",
        )
        self.viewer_user = self.create_user("report_viewer", group_name="Viewer")

        self.income_category = self.create_category(
            name="Donation",
            category_type="income",
        )
        self.expense_category = self.create_category(
            name="Rent",
            category_type="expense",
        )

    def _create_report_scenario(
        self,
        *,
        income_amount=Decimal("500.00"),
        expense_amount=Decimal("200.00"),
        transfer_amount=Decimal("100.00"),
    ):
        accounts = self._create_report_accounts()
        cash_account = accounts["cash_account"]
        online_donation_account = accounts["online_donation_account"]
        main_expense_account = accounts["main_expense_account"]

        self.create_transaction(
            transaction_type="income",
            amount=income_amount,
            target_account=online_donation_account,
            category=self.income_category,
            description="Sunday donation",
            created_by=self.admin_user,
        )
        self.create_transaction(
            transaction_type="expense",
            amount=expense_amount,
            source_account=cash_account,
            category=self.expense_category,
            description="Rent payment",
            created_by=self.admin_user,
        )
        self.create_transaction(
            transaction_type="transfer",
            amount=transfer_amount,
            source_account=online_donation_account,
            target_account=main_expense_account,
            description="Move donation funds",
            created_by=self.admin_user,
        )

        return accounts

    def _create_report_accounts(self):
        cash_account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
            opening_balance=Decimal("1000.00"),
        )
        online_donation_account = self.create_account(
            name="Online Donation Account",
            account_type="bank",
            account_purpose="online_donation",
            currency="TRY",
            opening_balance=Decimal("0.00"),
        )
        main_expense_account = self.create_account(
            name="Main Expense Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
            opening_balance=Decimal("0.00"),
        )

        return {
            "cash_account": cash_account,
            "online_donation_account": online_donation_account,
            "main_expense_account": main_expense_account,
        }

    def _login_viewer(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

    def test_logged_in_admin_can_access_report_dashboard(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.report_dashboard_url)

        self.assertEqual(response.status_code, 200)

    def test_logged_in_data_entry_user_can_access_report_dashboard(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.report_dashboard_url)

        self.assertEqual(response.status_code, 200)

    def test_logged_in_viewer_user_can_access_report_dashboard(self):
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected_to_login_from_report_dashboard(self):
        response = self.client.get(self.report_dashboard_url)

        login_url = resolve_url(settings.LOGIN_URL)
        expected_redirect = f"{login_url}?next={self.report_dashboard_url}"
        self.assertRedirects(
            response,
            expected_redirect,
            fetch_redirect_response=False,
        )

    def test_report_dashboard_displays_total_income(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Total Income")
        self.assertContains(response, "500.00")

    def test_report_dashboard_displays_total_expenses(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Total Expenses")
        self.assertContains(response, "200.00")

    def test_report_dashboard_displays_net_financial_status(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Net Financial Status")
        self.assertContains(response, "300.00")

    def test_report_dashboard_displays_account_balances(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Account Balances")
        self.assertContains(response, "800.00")
        self.assertContains(response, "400.00")
        self.assertContains(response, "100.00")

    def test_report_dashboard_displays_account_names(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Cash Account")
        self.assertContains(response, "Online Donation Account")
        self.assertContains(response, "Main Expense Account")

    def test_report_dashboard_displays_zero_state_when_there_are_no_transactions(self):
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Total Income")
        self.assertContains(response, "Total Expenses")
        self.assertContains(response, "Net Financial Status")
        self.assertContains(response, "0.00")

    def test_income_transaction_appears_in_total_income(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Total Income")
        self.assertContains(response, "500.00")

    def test_expense_transaction_appears_in_total_expenses(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Total Expenses")
        self.assertContains(response, "200.00")

    def test_transfer_transaction_is_not_included_in_total_income(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Total Income")
        self.assertContains(response, "500.00")
        self.assertNotContains(response, "600.00")

    def test_transfer_transaction_is_not_included_in_total_expenses(self):
        self._create_report_scenario(
            income_amount=Decimal("900.00"),
            expense_amount=Decimal("200.00"),
            transfer_amount=Decimal("125.00"),
        )
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Total Expenses")
        self.assertContains(response, "200.00")
        self.assertNotContains(response, "325.00")

    def test_net_financial_status_ignores_transfers(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Net Financial Status")
        self.assertContains(response, "300.00")

    def test_account_balance_starts_from_opening_balance(self):
        self._create_report_accounts()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Cash Account")
        self.assertContains(response, "1000.00")

    def test_account_balance_reflects_income_expense_and_transfer_movement(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Cash Account")
        self.assertContains(response, "800.00")
        self.assertContains(response, "Online Donation Account")
        self.assertContains(response, "400.00")
        self.assertContains(response, "Main Expense Account")
        self.assertContains(response, "100.00")
