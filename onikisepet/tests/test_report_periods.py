from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from onikisepet.usecases import financial_calculations, report_periods

from .helpers import TransactionTestMixin


class ReportPeriodTests(TestCase):
    def test_this_month_period(self):
        start, end, label = report_periods.resolve_report_period(
            "this_month",
            reference_date=date(2026, 6, 15),
        )

        self.assertEqual(start, date(2026, 6, 1))
        self.assertEqual(end, date(2026, 6, 30))
        self.assertEqual(label, "this_month")

    def test_last_month_period(self):
        start, end, label = report_periods.resolve_report_period(
            "last_month",
            reference_date=date(2026, 6, 15),
        )

        self.assertEqual(start, date(2026, 5, 1))
        self.assertEqual(end, date(2026, 5, 31))
        self.assertEqual(label, "last_month")

    def test_this_year_period(self):
        start, end, label = report_periods.resolve_report_period(
            "this_year",
            reference_date=date(2026, 6, 15),
        )

        self.assertEqual(start, date(2026, 1, 1))
        self.assertEqual(end, date(2026, 12, 31))
        self.assertEqual(label, "this_year")


class TransferSummaryTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.admin_user = self.create_user("transfer_summary_admin", is_superuser=True)
        self.cash = self.create_account(
            name="Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.bank = self.create_account(
            name="Bank",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )

    def test_build_transfer_summary_by_currency(self):
        self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("100.00"),
            source_account=self.bank,
            target_account=self.cash,
            created_by=self.admin_user,
        )

        transactions = self.get_transaction_model().objects.all()
        summary = financial_calculations.build_transfer_summary(transactions)

        self.assertEqual(summary["TRY"], Decimal("100.00"))
        self.assertEqual(summary["USD"], Decimal("0.00"))


class ReportDashboardPeriodViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.report_url = reverse("report_dashboard")
        self.viewer = self.create_user("report_period_viewer", group_name="Viewer")
        self.income_category = self.create_category(name="Bağış", category_type="income")
        self.cash = self.create_account(
            name="Cash Period",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )

    def test_this_month_preset_filters_report(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("300.00"),
            target_account=self.cash,
            category=self.income_category,
            date="2026-06-10",
            created_by=self.viewer,
        )
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("900.00"),
            target_account=self.cash,
            category=self.income_category,
            date="2026-05-10",
            created_by=self.viewer,
        )
        self.client.login(username=self.viewer.username, password=self.password)

        response = self.client.get(self.report_url, {"period": "this_month"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "300.00")
        self.assertNotContains(response, "900.00 TRY")

    def test_report_displays_transfer_summary(self):
        self.client.login(username=self.viewer.username, password=self.password)

        response = self.client.get(self.report_url)

        self.assertContains(response, "Transfer Özeti")
