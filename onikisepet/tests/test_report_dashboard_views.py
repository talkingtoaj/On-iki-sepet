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

    def _create_currency_summary_scenario(self):
        try_account = self.create_account(
            name="TRY Summary Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        usd_account = self.create_account(
            name="USD Summary Account",
            account_type="bank",
            account_purpose="foreign_currency",
            currency="USD",
        )
        eur_account = self.create_account(
            name="EUR Summary Account",
            account_type="bank",
            account_purpose="foreign_currency",
            currency="EUR",
        )

        self.create_transaction(
            transaction_type="income",
            amount=Decimal("500.00"),
            target_account=try_account,
            category=self.income_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            transaction_type="expense",
            amount=Decimal("200.00"),
            source_account=try_account,
            category=self.expense_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=usd_account,
            category=self.income_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            transaction_type="expense",
            amount=Decimal("25.00"),
            source_account=usd_account,
            category=self.expense_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("50.00"),
            target_account=eur_account,
            category=self.income_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            transaction_type="expense",
            amount=Decimal("5.00"),
            source_account=eur_account,
            category=self.expense_category,
            created_by=self.admin_user,
        )

    def _create_date_range_scenario(self):
        try_account = self.create_account(
            name="TRY Date Range Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        usd_account = self.create_account(
            name="USD Date Range Account",
            account_type="bank",
            account_purpose="foreign_currency",
            currency="USD",
        )
        try_transfer_target = self.create_account(
            name="TRY Date Range Transfer Target",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )

        self.create_transaction(
            date="2026-06-01",
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=try_account,
            category=self.income_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            date="2026-06-10",
            transaction_type="income",
            amount=Decimal("200.00"),
            target_account=try_account,
            category=self.income_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            date="2026-06-20",
            transaction_type="expense",
            amount=Decimal("50.00"),
            source_account=try_account,
            category=self.expense_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            date="2026-06-25",
            transaction_type="transfer",
            amount=Decimal("80.00"),
            source_account=try_account,
            target_account=try_transfer_target,
            created_by=self.admin_user,
        )
        self.create_transaction(
            date="2026-06-15",
            transaction_type="income",
            amount=Decimal("40.00"),
            target_account=usd_account,
            category=self.income_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            date="2026-07-01",
            transaction_type="income",
            amount=Decimal("300.00"),
            target_account=try_account,
            category=self.income_category,
            created_by=self.admin_user,
        )

    def _create_category_report_scenario(self):
        special_support_category = self.create_category(
            name="Special Support",
            category_type="income",
        )
        bills_category = self.create_category(
            name="Bills",
            category_type="expense",
        )

        try_cash_account = self.create_account(
            name="TRY Category Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        try_online_donation_account = self.create_account(
            name="TRY Category Online Donation Account",
            account_type="bank",
            account_purpose="online_donation",
            currency="TRY",
        )
        try_bank_account = self.create_account(
            name="TRY Category Bank Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        usd_bank_account = self.create_account(
            name="USD Category Bank Account",
            account_type="bank",
            account_purpose="foreign_currency",
            currency="USD",
        )
        try_transfer_target = self.create_account(
            name="TRY Category Transfer Target",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )

        self.create_transaction(
            date="2026-06-01",
            transaction_type="income",
            amount=Decimal("500.00"),
            target_account=try_cash_account,
            category=self.income_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            date="2026-06-10",
            transaction_type="income",
            amount=Decimal("200.00"),
            target_account=try_online_donation_account,
            category=self.income_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            date="2026-06-12",
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=usd_bank_account,
            category=self.income_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            date="2026-06-15",
            transaction_type="income",
            amount=Decimal("300.00"),
            target_account=try_cash_account,
            category=special_support_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            date="2026-06-18",
            transaction_type="expense",
            amount=Decimal("250.00"),
            source_account=try_cash_account,
            category=self.expense_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            date="2026-06-20",
            transaction_type="expense",
            amount=Decimal("75.00"),
            source_account=try_bank_account,
            category=bills_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            date="2026-06-22",
            transaction_type="expense",
            amount=Decimal("40.00"),
            source_account=usd_bank_account,
            category=self.expense_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            date="2026-06-25",
            transaction_type="transfer",
            amount=Decimal("999.00"),
            source_account=try_cash_account,
            target_account=try_transfer_target,
            created_by=self.admin_user,
        )

    def _create_category_date_range_scenario(self):
        try_cash_account = self.create_account(
            name="TRY Category Date Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )

        self.create_transaction(
            date="2026-06-01",
            transaction_type="income",
            amount=Decimal("500.00"),
            target_account=try_cash_account,
            category=self.income_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            date="2026-06-10",
            transaction_type="income",
            amount=Decimal("200.00"),
            target_account=try_cash_account,
            category=self.income_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            date="2026-06-20",
            transaction_type="expense",
            amount=Decimal("75.00"),
            source_account=try_cash_account,
            category=self.expense_category,
            created_by=self.admin_user,
        )
        self.create_transaction(
            date="2026-07-01",
            transaction_type="income",
            amount=Decimal("300.00"),
            target_account=try_cash_account,
            category=self.income_category,
            created_by=self.admin_user,
        )

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

    def test_report_dashboard_shows_start_and_end_date_inputs(self):
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, 'id="start_date"')
        self.assertContains(response, 'id="end_date"')
        self.assertContains(response, 'name="start_date"')
        self.assertContains(response, 'name="end_date"')
        self.assertContains(response, 'type="date"')
        self.assertNotContains(response, "flatpickr")

    def test_report_dashboard_displays_total_income(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Toplam Gelir")
        self.assertContains(response, "500.00")

    def test_report_dashboard_displays_total_expenses(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Toplam Gider")
        self.assertContains(response, "200.00")

    def test_report_dashboard_displays_net_financial_status(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Net Durum")
        self.assertContains(response, "300.00")

    def test_report_dashboard_displays_account_balances(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Hesap Bakiyeleri")
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

        self.assertContains(response, "Toplam Gelir")
        self.assertContains(response, "Toplam Gider")
        self.assertContains(response, "Net Durum")
        self.assertContains(response, "0.00")

    def test_income_transaction_appears_in_total_income(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Toplam Gelir")
        self.assertContains(response, "500.00")

    def test_expense_transaction_appears_in_total_expenses(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Toplam Gider")
        self.assertContains(response, "200.00")

    def test_transfer_transaction_is_not_included_in_total_income(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Toplam Gelir")
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

        self.assertContains(response, "Toplam Gider")
        self.assertContains(response, "200.00")
        self.assertNotContains(response, "325.00")

    def test_net_financial_status_ignores_transfers(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Net Durum")
        self.assertContains(response, "300.00")

    def test_account_balance_starts_from_opening_balance(self):
        self._create_report_accounts()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Cash Account")
        self.assertContains(response, "1,000.00")

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

    def test_report_dashboard_displays_try_summary_section(self):
        self._create_currency_summary_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "TRY Özeti")

    def test_report_dashboard_displays_usd_summary_section(self):
        self._create_currency_summary_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "USD Özeti")

    def test_report_dashboard_displays_eur_summary_section(self):
        self._create_currency_summary_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "EUR Özeti")

    def test_report_dashboard_displays_try_income_expense_and_net(self):
        self._create_currency_summary_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Toplam Gelir: 500.00 TRY")
        self.assertContains(response, "Toplam Gider: 200.00 TRY")
        self.assertContains(response, "Net Durum: 300.00 TRY")

    def test_report_dashboard_displays_usd_income_expense_and_net(self):
        self._create_currency_summary_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Toplam Gelir: 100.00 USD")
        self.assertContains(response, "Toplam Gider: 25.00 USD")
        self.assertContains(response, "Net Durum: 75.00 USD")

    def test_report_dashboard_displays_eur_income_expense_and_net(self):
        self._create_currency_summary_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Toplam Gelir: 50.00 EUR")
        self.assertContains(response, "Toplam Gider: 5.00 EUR")
        self.assertContains(response, "Net Durum: 45.00 EUR")

    def test_report_dashboard_does_not_display_combined_income_total_across_currencies(self):
        self._create_currency_summary_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertNotContains(response, "650.00")

    def test_report_dashboard_does_not_display_combined_expense_total_across_currencies(self):
        self._create_currency_summary_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertNotContains(response, "230.00")

    def test_report_dashboard_does_not_display_combined_net_total_across_currencies(self):
        self._create_currency_summary_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertNotContains(response, "420.00")

    def test_report_dashboard_displays_zero_currency_summaries_when_no_transactions(self):
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "TRY Özeti")
        self.assertContains(response, "Toplam Gelir: 0.00 TRY")
        self.assertContains(response, "Toplam Gider: 0.00 TRY")
        self.assertContains(response, "Net Durum: 0.00 TRY")
        self.assertContains(response, "USD Özeti")
        self.assertContains(response, "Toplam Gelir: 0.00 USD")
        self.assertContains(response, "Toplam Gider: 0.00 USD")
        self.assertContains(response, "Net Durum: 0.00 USD")
        self.assertContains(response, "EUR Özeti")
        self.assertContains(response, "Toplam Gelir: 0.00 EUR")
        self.assertContains(response, "Toplam Gider: 0.00 EUR")
        self.assertContains(response, "Net Durum: 0.00 EUR")

    def test_report_dashboard_without_date_filter_shows_all_transactions(self):
        self._create_date_range_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Toplam Gelir: 600.00 TRY")
        self.assertContains(response, "Toplam Gider: 50.00 TRY")
        self.assertContains(response, "Net Durum: 550.00 TRY")

    def test_report_dashboard_with_start_date_only_excludes_older_transactions(self):
        self._create_date_range_scenario()
        self._login_viewer()

        response = self.client.get(
            self.report_dashboard_url,
            {"start_date": "2026-06-15"},
        )

        self.assertContains(response, "Toplam Gelir: 300.00 TRY")
        self.assertContains(response, "Toplam Gider: 50.00 TRY")
        self.assertContains(response, "Net Durum: 250.00 TRY")
        self.assertNotContains(response, "600.00 TRY")

    def test_report_dashboard_with_end_date_only_excludes_later_transactions(self):
        self._create_date_range_scenario()
        self._login_viewer()

        response = self.client.get(
            self.report_dashboard_url,
            {"end_date": "2026-06-30"},
        )

        self.assertContains(response, "Toplam Gelir: 300.00 TRY")
        self.assertContains(response, "Toplam Gider: 50.00 TRY")
        self.assertContains(response, "Net Durum: 250.00 TRY")
        self.assertNotContains(response, "600.00 TRY")

    def test_report_dashboard_with_date_range_shows_only_transactions_inside_range(self):
        self._create_date_range_scenario()
        self._login_viewer()

        response = self.client.get(
            self.report_dashboard_url,
            {"start_date": "2026-06-01", "end_date": "2026-06-30"},
        )

        self.assertContains(response, "Toplam Gelir: 300.00 TRY")
        self.assertContains(response, "Toplam Gider: 50.00 TRY")
        self.assertContains(response, "Net Durum: 250.00 TRY")
        self.assertNotContains(response, "600.00 TRY")

    def test_currency_summary_respects_date_range(self):
        self._create_date_range_scenario()
        self._login_viewer()

        response = self.client.get(
            self.report_dashboard_url,
            {"start_date": "2026-06-01", "end_date": "2026-06-30"},
        )

        self.assertContains(response, "Toplam Gelir: 300.00 TRY")
        self.assertContains(response, "Toplam Gider: 50.00 TRY")
        self.assertContains(response, "Net Durum: 250.00 TRY")
        self.assertContains(response, "Toplam Gelir: 40.00 USD")
        self.assertContains(response, "Toplam Gider: 0.00 USD")
        self.assertContains(response, "Net Durum: 40.00 USD")

    def test_date_filtered_report_still_does_not_count_transfers_as_income_or_expense(self):
        self._create_date_range_scenario()
        self._login_viewer()

        response = self.client.get(
            self.report_dashboard_url,
            {"start_date": "2026-06-15", "end_date": "2026-06-30"},
        )

        self.assertContains(response, "Toplam Gelir: 0.00 TRY")
        self.assertContains(response, "Toplam Gider: 50.00 TRY")
        self.assertContains(response, "Net Durum: -50.00 TRY")
        self.assertNotContains(response, "Toplam Gelir: 80.00 TRY")
        self.assertNotContains(response, "Toplam Gider: 130.00 TRY")

    def test_account_balances_ignore_date_filter(self):
        accounts = self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(
            self.report_dashboard_url,
            {"start_date": "2099-01-01", "end_date": "2099-12-31"},
        )

        self.assertContains(response, "Toplam Gelir: 0.00 TRY")
        self.assertContains(response, "Toplam Gider: 0.00 TRY")
        self.assertContains(response, "Cash Account")
        self.assertContains(response, "800.00")
        self.assertContains(response, "Online Donation Account")
        self.assertContains(response, "400.00")
        self.assertContains(response, "Main Expense Account")
        self.assertContains(response, "100.00")

    def test_report_dashboard_displays_transfer_movements(self):
        self._create_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Move donation funds")
        self.assertContains(response, "100.00 TRY")

    def test_transfer_movements_respect_date_filter(self):
        accounts = self._create_report_accounts()
        self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("50.00"),
            source_account=accounts["online_donation_account"],
            target_account=accounts["main_expense_account"],
            description="June transfer",
            date="2026-06-10",
            created_by=self.admin_user,
        )
        self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("75.00"),
            source_account=accounts["cash_account"],
            target_account=accounts["main_expense_account"],
            description="July transfer",
            date="2026-07-10",
            created_by=self.admin_user,
        )
        self._login_viewer()

        response = self.client.get(
            self.report_dashboard_url,
            {"start_date": "2026-06-01", "end_date": "2026-06-30"},
        )

        self.assertContains(response, "June transfer")
        self.assertNotContains(response, "July transfer")

    def test_report_dashboard_with_invalid_start_date_does_not_crash(self):
        self._create_date_range_scenario()
        self._login_viewer()

        response = self.client.get(
            self.report_dashboard_url,
            {"start_date": "not-a-date"},
        )

        self.assertEqual(response.status_code, 200)

    def test_report_dashboard_with_invalid_end_date_does_not_crash(self):
        self._create_date_range_scenario()
        self._login_viewer()

        response = self.client.get(
            self.report_dashboard_url,
            {"end_date": "not-a-date"},
        )

        self.assertEqual(response.status_code, 200)

    def test_report_dashboard_displays_income_by_category_section(self):
        self._create_category_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Kategoriye Göre Gelir")

    def test_report_dashboard_displays_income_category_totals(self):
        self._create_category_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Donation")
        self.assertContains(response, "700.00 TRY")
        self.assertContains(response, "Special Support")
        self.assertContains(response, "300.00 TRY")

    def test_report_dashboard_income_category_totals_show_currency(self):
        self._create_category_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Donation")
        self.assertContains(response, "700.00 TRY")
        self.assertContains(response, "100.00 USD")

    def test_report_dashboard_income_category_totals_do_not_include_expenses(self):
        self._create_category_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Donation")
        self.assertContains(response, "700.00 TRY")
        self.assertNotContains(response, "950.00 TRY")

    def test_report_dashboard_income_category_totals_do_not_include_transfers(self):
        self._create_category_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Donation")
        self.assertContains(response, "700.00 TRY")
        self.assertNotContains(response, "1,699.00 TRY")

    def test_report_dashboard_displays_expenses_by_category_section(self):
        self._create_category_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Kategoriye Göre Gider")

    def test_report_dashboard_displays_expense_category_totals(self):
        self._create_category_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Rent")
        self.assertContains(response, "250.00 TRY")
        self.assertContains(response, "Bills")
        self.assertContains(response, "75.00 TRY")
        self.assertNotContains(response, "En yüksek 5 gider kalemi")

    def test_report_dashboard_expense_category_totals_show_currency(self):
        self._create_category_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Rent")
        self.assertContains(response, "250.00 TRY")
        self.assertContains(response, "40.00 USD")

    def test_report_dashboard_expense_category_totals_do_not_include_income(self):
        self._create_category_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Rent")
        self.assertContains(response, "250.00 TRY")
        self.assertNotContains(response, "950.00 TRY")

    def test_report_dashboard_expense_category_totals_do_not_include_transfers(self):
        self._create_category_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Rent")
        self.assertContains(response, "250.00 TRY")
        self.assertNotContains(response, "1,249.00 TRY")

    def test_report_dashboard_category_totals_do_not_mix_currencies(self):
        self._create_category_report_scenario()
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Donation")
        self.assertContains(response, "700.00 TRY")
        self.assertContains(response, "100.00 USD")
        self.assertContains(response, "Rent")
        self.assertContains(response, "250.00 TRY")
        self.assertContains(response, "40.00 USD")
        self.assertNotContains(response, "800.00 TRY")
        self.assertNotContains(response, "290.00 TRY")

    def test_report_dashboard_category_totals_respect_date_range(self):
        self._create_category_date_range_scenario()
        self._login_viewer()

        response = self.client.get(
            self.report_dashboard_url,
            {"start_date": "2026-06-01", "end_date": "2026-06-30"},
        )

        self.assertContains(response, "Donation")
        self.assertContains(response, "700.00 TRY")
        self.assertContains(response, "Rent")
        self.assertContains(response, "75.00 TRY")
        self.assertNotContains(response, "1,000.00 TRY")

    def test_report_dashboard_displays_empty_income_category_message_when_no_income(self):
        self.create_transaction(
            transaction_type="expense",
            amount=Decimal("75.00"),
            source_account=self.create_account(name="No Income Cash Account"),
            category=self.expense_category,
            created_by=self.admin_user,
        )
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Gelir kategorisi bulunamadı.")

    def test_report_dashboard_displays_empty_expense_category_message_when_no_expenses(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("500.00"),
            target_account=self.create_account(name="No Expense Cash Account"),
            category=self.income_category,
            created_by=self.admin_user,
        )
        self._login_viewer()

        response = self.client.get(self.report_dashboard_url)

        self.assertContains(response, "Gider kategorisi bulunamadı.")
