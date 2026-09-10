from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .helpers import ExchangeRateTestMixin, TransactionTestMixin


class ReportDashboardMultiCurrencyTests(
    ExchangeRateTestMixin, TransactionTestMixin, TestCase
):
    """The dashboard must never present one number that spans currencies
    without saying what rate produced it.
    """

    def setUp(self):
        self.url = reverse("report_dashboard")
        self.user = self.create_user("dashboard_fx_user", is_superuser=True)
        self.income_category = self.create_category(
            name="Donation",
            category_type="income",
        )
        self.try_account = self.create_account(
            name="TRY Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.usd_account = self.create_account(
            name="USD Bank",
            account_type="bank",
            account_purpose="foreign_currency",
            currency="USD",
        )
        self.client.login(username=self.user.username, password=self.password)

    def _income(self, account, amount):
        return self.create_transaction(
            transaction_type="income",
            amount=amount,
            target_account=account,
            category=self.income_category,
            created_by=self.user,
        )

    def _mixed_scenario(self):
        self._income(self.try_account, Decimal("1000.00"))
        self._income(self.usd_account, Decimal("100.00"))

    def test_dashboard_never_adds_try_and_usd_into_one_figure(self):
        """The original bug: 1000 TRY + 100 USD rendered as 1100.00."""
        self._mixed_scenario()

        response = self.client.get(self.url)

        self.assertNotContains(response, "1100.00")

    def test_dashboard_shows_a_separate_block_per_currency(self):
        self._mixed_scenario()

        response = self.client.get(self.url)

        self.assertContains(response, "1000.00")
        self.assertContains(response, "100.00")
        self.assertContains(response, "TRY")
        self.assertContains(response, "USD")

    def test_dashboard_labels_each_account_balance_with_its_currency(self):
        self._mixed_scenario()

        response = self.client.get(self.url)

        self.assertContains(response, "TRY Cash")
        self.assertContains(response, "USD Bank")
        self.assertContains(response, "100.00 USD")

    def test_dashboard_shows_a_converted_grand_total_when_rates_exist(self):
        self._mixed_scenario()
        self.create_exchange_rate(
            currency="USD",
            rate_to_base=Decimal("34.00"),
            effective_date="2026-09-01",
        )

        response = self.client.get(self.url)

        # 1000 TRY + (100 USD x 34.00) = 4400.00 TRY
        self.assertContains(response, "Grand Total")
        self.assertContains(response, "4400.00")

    def test_dashboard_shows_which_rate_was_used(self):
        self._mixed_scenario()
        self.create_exchange_rate(
            currency="USD",
            rate_to_base=Decimal("34.00"),
            effective_date="2026-09-01",
        )

        response = self.client.get(self.url)

        self.assertContains(response, "34.00")
        self.assertContains(response, "Sept. 1, 2026")

    def test_dashboard_warns_when_a_rate_is_missing(self):
        self._mixed_scenario()

        response = self.client.get(self.url)

        self.assertContains(response, "USD")
        self.assertContains(response, "no exchange rate")

    def test_dashboard_does_not_present_an_incomplete_total_as_complete(self):
        """With no USD rate the USD holdings cannot be converted. The total
        must be marked incomplete rather than quietly excluding them.
        """
        self._mixed_scenario()

        response = self.client.get(self.url)

        self.assertContains(response, "incomplete")
