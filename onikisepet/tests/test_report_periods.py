"""Date-range filtering for reports.

Income and expense figures are period-scoped. Account balances deliberately are
not: a balance is the cumulative position, so filtering it to "this month"
would silently drop the opening position and report a false balance.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import translation

from onikisepet.usecases import report_periods
from onikisepet.usecases.roles import TREASURER

from .helpers import TransactionTestMixin


@override_settings(LANGUAGE_CODE="en")
class ResolvePeriodTests(TestCase):
    reference = date(2026, 9, 10)

    def test_all_time_has_no_bounds(self):
        start, end = report_periods.resolve_report_period(
            "all", reference_date=self.reference
        )

        self.assertIsNone(start)
        self.assertIsNone(end)

    def test_missing_value_defaults_to_all_time(self):
        for value in [None, "", "nonsense"]:
            start, end = report_periods.resolve_report_period(
                value, reference_date=self.reference
            )
            self.assertIsNone(start, value)
            self.assertIsNone(end, value)

    def test_this_month_spans_the_calendar_month(self):
        start, end = report_periods.resolve_report_period(
            "this_month", reference_date=self.reference
        )

        self.assertEqual(start, date(2026, 9, 1))
        self.assertEqual(end, date(2026, 9, 30))

    def test_last_month_spans_the_previous_calendar_month(self):
        start, end = report_periods.resolve_report_period(
            "last_month", reference_date=self.reference
        )

        self.assertEqual(start, date(2026, 8, 1))
        self.assertEqual(end, date(2026, 8, 31))

    def test_last_month_crosses_the_year_boundary(self):
        start, end = report_periods.resolve_report_period(
            "last_month", reference_date=date(2026, 1, 15)
        )

        self.assertEqual(start, date(2025, 12, 1))
        self.assertEqual(end, date(2025, 12, 31))

    def test_this_month_handles_february_in_a_leap_year(self):
        start, end = report_periods.resolve_report_period(
            "this_month", reference_date=date(2028, 2, 10)
        )

        self.assertEqual(start, date(2028, 2, 1))
        self.assertEqual(end, date(2028, 2, 29))

    def test_this_year_spans_the_calendar_year(self):
        start, end = report_periods.resolve_report_period(
            "this_year", reference_date=self.reference
        )

        self.assertEqual(start, date(2026, 1, 1))
        self.assertEqual(end, date(2026, 12, 31))

    def test_period_choices_are_offered_for_the_selector(self):
        values = [value for value, _label in report_periods.period_choices()]

        self.assertEqual(values, ["all", "this_month", "last_month", "this_year"])

    def test_labels_are_translated(self):
        with translation.override("tr"):
            labels = dict(report_periods.period_choices())
            self.assertEqual(str(labels["this_month"]), "Bu ay")


@override_settings(LANGUAGE_CODE="en")
class DashboardPeriodTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("period_user", group_name=TREASURER)
        self.account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
            opening_balance=Decimal("1000.00"),
        )
        self.income_category = self.create_category(
            name="Donation", category_type="income"
        )
        self.url = reverse("report_dashboard")
        self.client.login(username=self.user.username, password=self.password)
        self.calculations = self.get_financial_calculations_module()

    def _income(self, amount, on_date):
        return self.create_transaction(
            transaction_type="income",
            amount=amount,
            target_account=self.account,
            category=self.income_category,
            created_by=self.user,
            date=on_date,
        )

    def test_all_time_includes_everything(self):
        self._income(Decimal("100.00"), "2026-01-15")
        self._income(Decimal("200.00"), "2026-09-05")

        response = self.client.get(self.url, {"period": "all"})

        block = response.context["currency_blocks"][0]
        self.assertEqual(block.income, Decimal("300.00"))

    def test_this_year_excludes_a_prior_year(self):
        self._income(Decimal("100.00"), "2025-06-15")
        self._income(Decimal("200.00"), "2026-09-05")

        response = self.client.get(self.url, {"period": "this_year"})

        block = response.context["currency_blocks"][0]
        self.assertEqual(block.income, Decimal("200.00"))

    def test_period_boundaries_are_inclusive(self):
        """A transaction on the first or last day of the month belongs to it."""
        self._income(Decimal("10.00"), "2026-09-01")
        self._income(Decimal("20.00"), "2026-09-30")
        self._income(Decimal("40.00"), "2026-08-31")

        response = self.client.get(self.url, {"period": "this_month"})

        block = response.context["currency_blocks"][0]
        self.assertEqual(block.income, Decimal("30.00"))

    def test_account_balances_are_never_period_filtered(self):
        """The balance is cumulative. Scoping it to a period would drop the
        opening balance and every earlier movement, reporting a false figure.
        """
        self._income(Decimal("500.00"), "2025-03-10")

        response = self.client.get(self.url, {"period": "this_month"})

        balances = {
            item["account"].name: item["balance"]
            for item in response.context["account_balances"]
        }
        self.assertEqual(balances["Cash Account"], Decimal("1500.00"))

    def test_dashboard_shows_the_active_period(self):
        response = self.client.get(self.url, {"period": "this_month"})

        self.assertContains(response, "This month")

    def test_dashboard_offers_the_period_selector(self):
        response = self.client.get(self.url)

        self.assertContains(response, 'name="period"')
        self.assertContains(response, "this_month")
        self.assertContains(response, "last_month")

    def test_unknown_period_falls_back_to_all_time(self):
        self._income(Decimal("100.00"), "2020-01-01")

        response = self.client.get(self.url, {"period": "banana"})

        block = response.context["currency_blocks"][0]
        self.assertEqual(block.income, Decimal("100.00"))

    def test_default_period_is_all_time(self):
        self._income(Decimal("100.00"), "2020-01-01")

        response = self.client.get(self.url)

        block = response.context["currency_blocks"][0]
        self.assertEqual(block.income, Decimal("100.00"))
