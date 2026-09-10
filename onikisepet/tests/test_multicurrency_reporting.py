from datetime import date
from decimal import Decimal

from django.test import TestCase

from .helpers import ExchangeRateTestMixin, TransactionTestMixin


class MultiCurrencyTotalsTests(ExchangeRateTestMixin, TransactionTestMixin, TestCase):
    """Money in different currencies must never be added together.

    These tests protect the project's highest-priority rule: a TRY figure and a
    USD figure are not commensurable, so any total that spans both is either
    grouped by currency or explicitly converted at a known rate.
    """

    def setUp(self):
        self.user = self.create_user("multicurrency_user", is_superuser=True)
        self.income_category = self.create_category(
            name="Donation",
            category_type="income",
        )
        self.expense_category = self.create_category(
            name="Rent",
            category_type="expense",
        )
        self.try_account = self.create_account(
            name="TRY Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
            opening_balance=Decimal("0.00"),
        )
        self.usd_account = self.create_account(
            name="USD Bank",
            account_type="bank",
            account_purpose="foreign_currency",
            currency="USD",
            opening_balance=Decimal("0.00"),
        )
        self.eur_account = self.create_account(
            name="EUR Bank",
            account_type="bank",
            account_purpose="foreign_currency",
            currency="EUR",
            opening_balance=Decimal("0.00"),
        )
        self.calculations = self.get_financial_calculations_module()

    def _income(self, account, amount):
        return self.create_transaction(
            transaction_type="income",
            amount=amount,
            target_account=account,
            category=self.income_category,
            created_by=self.user,
        )

    def _expense(self, account, amount):
        return self.create_transaction(
            transaction_type="expense",
            amount=amount,
            source_account=account,
            category=self.expense_category,
            created_by=self.user,
        )

    # --- grouping ---------------------------------------------------------

    def test_income_totals_are_grouped_by_currency(self):
        self._income(self.try_account, Decimal("1000.00"))
        self._income(self.usd_account, Decimal("100.00"))

        totals = self.calculations.calculate_income_total_by_currency(
            self.get_transaction_model().objects.all()
        )

        self.assertEqual(totals["TRY"], Decimal("1000.00"))
        self.assertEqual(totals["USD"], Decimal("100.00"))

    def test_expense_totals_are_grouped_by_currency(self):
        self._expense(self.try_account, Decimal("200.00"))
        self._expense(self.usd_account, Decimal("50.00"))

        totals = self.calculations.calculate_expense_total_by_currency(
            self.get_transaction_model().objects.all()
        )

        self.assertEqual(totals["TRY"], Decimal("200.00"))
        self.assertEqual(totals["USD"], Decimal("50.00"))

    def test_transfer_totals_are_grouped_by_currency_and_stay_separate(self):
        self._income(self.try_account, Decimal("1000.00"))
        self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("300.00"),
            source_account=self.try_account,
            target_account=self.create_account(
                name="Other TRY",
                account_type="bank",
                account_purpose="main_expense",
                currency="TRY",
            ),
            created_by=self.user,
        )

        transfers = self.calculations.calculate_transfer_total_by_currency(
            self.get_transaction_model().objects.all()
        )
        income = self.calculations.calculate_income_total_by_currency(
            self.get_transaction_model().objects.all()
        )

        self.assertEqual(transfers["TRY"], Decimal("300.00"))
        self.assertEqual(income["TRY"], Decimal("1000.00"))

    def test_summarise_by_currency_reports_income_expenses_and_net_per_currency(self):
        self._income(self.try_account, Decimal("1000.00"))
        self._expense(self.try_account, Decimal("400.00"))
        self._income(self.usd_account, Decimal("100.00"))

        summaries = {
            summary.currency: summary
            for summary in self.calculations.summarise_by_currency(
                self.get_transaction_model().objects.all()
            )
        }

        self.assertEqual(summaries["TRY"].income, Decimal("1000.00"))
        self.assertEqual(summaries["TRY"].expenses, Decimal("400.00"))
        self.assertEqual(summaries["TRY"].net, Decimal("600.00"))
        self.assertEqual(summaries["USD"].income, Decimal("100.00"))
        self.assertEqual(summaries["USD"].expenses, Decimal("0.00"))
        self.assertEqual(summaries["USD"].net, Decimal("100.00"))

    # --- the currency-blind helpers must refuse mixed data ----------------

    def test_income_total_refuses_to_add_two_currencies_together(self):
        self._income(self.try_account, Decimal("1000.00"))
        self._income(self.usd_account, Decimal("100.00"))

        with self.assertRaises(self.calculations.MixedCurrencyError):
            self.calculations.calculate_income_total(
                self.get_transaction_model().objects.all()
            )

    def test_expense_total_refuses_to_add_two_currencies_together(self):
        self._expense(self.try_account, Decimal("200.00"))
        self._expense(self.usd_account, Decimal("50.00"))

        with self.assertRaises(self.calculations.MixedCurrencyError):
            self.calculations.calculate_expense_total(
                self.get_transaction_model().objects.all()
            )

    def test_income_total_accepts_an_explicit_currency_filter(self):
        self._income(self.try_account, Decimal("1000.00"))
        self._income(self.usd_account, Decimal("100.00"))

        total = self.calculations.calculate_income_total(
            self.get_transaction_model().objects.all(),
            currency="USD",
        )

        self.assertEqual(total, Decimal("100.00"))

    def test_total_net_position_refuses_to_add_two_currencies_together(self):
        with self.assertRaises(self.calculations.MixedCurrencyError):
            self.calculations.calculate_total_net_position(
                [self.try_account, self.usd_account]
            )

    def test_account_balances_are_grouped_by_currency(self):
        self._income(self.try_account, Decimal("1000.00"))
        self._income(self.usd_account, Decimal("100.00"))

        balances = self.calculations.calculate_account_balances_by_currency(
            self.get_account_model().objects.all()
        )

        self.assertEqual(balances["TRY"], Decimal("1000.00"))
        self.assertEqual(balances["USD"], Decimal("100.00"))
        self.assertEqual(balances["EUR"], Decimal("0.00"))

    # --- conversion -------------------------------------------------------

    def test_convert_to_base_returns_the_amount_unchanged_for_base_currency(self):
        converted = self.calculations.convert_to_base(
            Decimal("1000.00"), "TRY", date(2026, 9, 9)
        )

        self.assertEqual(converted, Decimal("1000.00"))

    def test_convert_to_base_applies_the_rate(self):
        self.create_exchange_rate(
            currency="USD",
            rate_to_base=Decimal("34.00"),
            effective_date="2026-09-01",
        )

        converted = self.calculations.convert_to_base(
            Decimal("100.00"), "USD", date(2026, 9, 9)
        )

        self.assertEqual(converted, Decimal("3400.00"))

    def test_convert_to_base_returns_none_when_no_rate_is_available(self):
        converted = self.calculations.convert_to_base(
            Decimal("100.00"), "USD", date(2026, 9, 9)
        )

        self.assertIsNone(converted)

    def test_grand_total_converts_every_currency_and_reports_the_rates_used(self):
        self.create_exchange_rate(
            currency="USD",
            rate_to_base=Decimal("34.00"),
            effective_date="2026-09-01",
        )

        grand_total = self.calculations.calculate_grand_total_in_base(
            {"TRY": Decimal("6800.00"), "USD": Decimal("100.00")},
            on_date=date(2026, 9, 9),
        )

        self.assertEqual(grand_total.total, Decimal("10200.00"))
        self.assertTrue(grand_total.is_complete)
        self.assertEqual(grand_total.base_currency, "TRY")
        usd_conversion = next(
            conversion
            for conversion in grand_total.conversions
            if conversion.currency == "USD"
        )
        self.assertEqual(usd_conversion.rate, Decimal("34.00"))
        self.assertEqual(usd_conversion.rate_date, date(2026, 9, 1))
        self.assertEqual(usd_conversion.converted, Decimal("3400.00"))

    def test_grand_total_flags_a_missing_rate_instead_of_treating_it_as_zero(self):
        """A missing rate must be visible. Quietly dropping the amount would
        understate the total, which is worse than showing an incomplete figure.
        """
        self.create_exchange_rate(
            currency="USD",
            rate_to_base=Decimal("34.00"),
            effective_date="2026-09-01",
        )

        grand_total = self.calculations.calculate_grand_total_in_base(
            {
                "TRY": Decimal("6800.00"),
                "USD": Decimal("100.00"),
                "EUR": Decimal("50.00"),
            },
            on_date=date(2026, 9, 9),
        )

        self.assertFalse(grand_total.is_complete)
        self.assertEqual(grand_total.missing_currencies, ["EUR"])
        self.assertEqual(grand_total.total, Decimal("10200.00"))

    def test_grouping_merges_rows_that_differ_only_by_date(self):
        """Grouping is by currency and nothing else.

        Transaction has a model-level Meta.ordering. Some Django versions used
        to fold ordering fields into the GROUP BY of a values().annotate(),
        which would split one currency into one row per date and under-report
        the total. This pins the invariant whichever way the ORM behaves.
        """
        self._income(self.try_account, Decimal("100.00"))
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("250.00"),
            target_account=self.try_account,
            category=self.income_category,
            created_by=self.user,
            date="2026-01-15",
        )
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("400.00"),
            target_account=self.try_account,
            category=self.income_category,
            created_by=self.user,
            date="2026-02-20",
        )

        totals = self.calculations.calculate_income_total_by_currency(
            self.get_transaction_model().objects.all()
        )

        self.assertEqual(list(totals), ["TRY"])
        self.assertEqual(totals["TRY"], Decimal("750.00"))

    # --- the regression that started all of this --------------------------

    def test_one_thousand_try_plus_one_hundred_usd_is_never_eleven_hundred(self):
        self._income(self.try_account, Decimal("1000.00"))
        self._income(self.usd_account, Decimal("100.00"))

        totals = self.calculations.calculate_income_total_by_currency(
            self.get_transaction_model().objects.all()
        )

        self.assertEqual(sorted(totals), ["TRY", "USD"])
        self.assertNotIn(Decimal("1100.00"), totals.values())
