from datetime import date
from decimal import Decimal

from django.test import TestCase

from .helpers import TransactionTestMixin


class CategoryFinancialCalculationTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("category_report_user")
        self.donation_category = self.create_category(
            name="Donation",
            category_type="income",
        )
        self.special_support_category = self.create_category(
            name="Special Support",
            category_type="income",
        )
        self.rent_category = self.create_category(
            name="Rent",
            category_type="expense",
        )
        self.bills_category = self.create_category(
            name="Bills",
            category_type="expense",
        )

        self.try_cash_account = self.create_account(
            name="TRY Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.try_bank_account = self.create_account(
            name="TRY Bank Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.try_online_donation_account = self.create_account(
            name="TRY Online Donation Account",
            account_type="bank",
            account_purpose="online_donation",
            currency="TRY",
        )
        self.usd_bank_account = self.create_account(
            name="USD Bank Account",
            account_type="bank",
            account_purpose="foreign_currency",
            currency="USD",
        )
        self.usd_savings_account = self.create_account(
            name="USD Savings Account",
            account_type="savings",
            account_purpose="savings",
            currency="USD",
        )
        self.eur_bank_account = self.create_account(
            name="EUR Bank Account",
            account_type="bank",
            account_purpose="foreign_currency",
            currency="EUR",
        )
        self.eur_savings_account = self.create_account(
            name="EUR Savings Account",
            account_type="savings",
            account_purpose="savings",
            currency="EUR",
        )

        self.calculations = self.get_financial_calculations_module()

    def _transactions(self):
        return self.get_transaction_model().objects.all()

    def _find_total(self, results, *, category, currency):
        for item in results:
            if item["category"] == category and item["currency"] == currency:
                return item["total"]
        raise AssertionError(
            f"Expected total for category={category.name}, currency={currency}."
        )

    def _assert_missing_total(self, results, *, category, currency):
        matching_items = [
            item
            for item in results
            if item["category"] == category and item["currency"] == currency
        ]
        self.assertEqual(matching_items, [])

    def _create_income(
        self,
        *,
        amount,
        account,
        category=None,
        transaction_date=date(2026, 6, 10),
    ):
        return self.create_transaction(
            date=transaction_date,
            transaction_type="income",
            amount=amount,
            target_account=account,
            category=category or self.donation_category,
            created_by=self.user,
        )

    def _create_expense(
        self,
        *,
        amount,
        account,
        category=None,
        transaction_date=date(2026, 6, 10),
    ):
        return self.create_transaction(
            date=transaction_date,
            transaction_type="expense",
            amount=amount,
            source_account=account,
            category=category or self.rent_category,
            created_by=self.user,
        )

    def _create_transfer(
        self,
        *,
        amount=Decimal("999.00"),
        source_account=None,
        target_account=None,
        transaction_date=date(2026, 6, 10),
    ):
        return self.create_transaction(
            date=transaction_date,
            transaction_type="transfer",
            amount=amount,
            source_account=source_account or self.try_cash_account,
            target_account=target_account or self.try_bank_account,
            created_by=self.user,
        )

    def _create_category_report_scenario(self):
        self._create_income(
            amount=Decimal("500.00"),
            account=self.try_cash_account,
            category=self.donation_category,
        )
        self._create_income(
            amount=Decimal("200.00"),
            account=self.try_online_donation_account,
            category=self.donation_category,
        )
        self._create_income(
            amount=Decimal("100.00"),
            account=self.usd_bank_account,
            category=self.donation_category,
        )
        self._create_income(
            amount=Decimal("300.00"),
            account=self.try_cash_account,
            category=self.special_support_category,
        )
        self._create_expense(
            amount=Decimal("250.00"),
            account=self.try_cash_account,
            category=self.rent_category,
        )
        self._create_expense(
            amount=Decimal("75.00"),
            account=self.try_bank_account,
            category=self.bills_category,
        )
        self._create_expense(
            amount=Decimal("40.00"),
            account=self.usd_bank_account,
            category=self.rent_category,
        )
        self._create_transfer()

    def test_income_totals_by_category_includes_income_transactions(self):
        self._create_category_report_scenario()

        results = self.calculations.calculate_income_totals_by_category(
            self._transactions(),
        )

        self.assertEqual(
            self._find_total(results, category=self.donation_category, currency="TRY"),
            Decimal("700.00"),
        )

    def test_income_totals_by_category_excludes_expense_transactions(self):
        self._create_category_report_scenario()

        results = self.calculations.calculate_income_totals_by_category(
            self._transactions(),
        )

        self._assert_missing_total(results, category=self.rent_category, currency="TRY")
        self._assert_missing_total(results, category=self.bills_category, currency="TRY")

    def test_income_totals_by_category_excludes_transfer_transactions(self):
        self._create_category_report_scenario()

        results = self.calculations.calculate_income_totals_by_category(
            self._transactions(),
        )

        totals = [item["total"] for item in results]
        self.assertNotIn(Decimal("999.00"), totals)

    def test_income_totals_by_category_groups_by_category(self):
        self._create_category_report_scenario()

        results = self.calculations.calculate_income_totals_by_category(
            self._transactions(),
        )

        self.assertEqual(
            self._find_total(results, category=self.donation_category, currency="TRY"),
            Decimal("700.00"),
        )
        self.assertEqual(
            self._find_total(
                results,
                category=self.special_support_category,
                currency="TRY",
            ),
            Decimal("300.00"),
        )

    def test_income_totals_by_category_groups_by_currency(self):
        self._create_category_report_scenario()

        results = self.calculations.calculate_income_totals_by_category(
            self._transactions(),
        )

        self.assertEqual(
            self._find_total(results, category=self.donation_category, currency="TRY"),
            Decimal("700.00"),
        )
        self.assertEqual(
            self._find_total(results, category=self.donation_category, currency="USD"),
            Decimal("100.00"),
        )

    def test_income_totals_by_category_returns_empty_when_no_income(self):
        self._create_expense(
            amount=Decimal("75.00"),
            account=self.try_cash_account,
            category=self.bills_category,
        )
        self._create_transfer()

        results = self.calculations.calculate_income_totals_by_category(
            self._transactions(),
        )

        self.assertEqual(results, [])

    def test_expense_totals_by_category_includes_expense_transactions(self):
        self._create_category_report_scenario()

        results = self.calculations.calculate_expense_totals_by_category(
            self._transactions(),
        )

        self.assertEqual(
            self._find_total(results, category=self.rent_category, currency="TRY"),
            Decimal("250.00"),
        )

    def test_expense_totals_by_category_excludes_income_transactions(self):
        self._create_category_report_scenario()

        results = self.calculations.calculate_expense_totals_by_category(
            self._transactions(),
        )

        self._assert_missing_total(
            results,
            category=self.donation_category,
            currency="TRY",
        )
        self._assert_missing_total(
            results,
            category=self.special_support_category,
            currency="TRY",
        )

    def test_expense_totals_by_category_excludes_transfer_transactions(self):
        self._create_category_report_scenario()

        results = self.calculations.calculate_expense_totals_by_category(
            self._transactions(),
        )

        totals = [item["total"] for item in results]
        self.assertNotIn(Decimal("999.00"), totals)

    def test_expense_totals_by_category_groups_by_category(self):
        self._create_category_report_scenario()

        results = self.calculations.calculate_expense_totals_by_category(
            self._transactions(),
        )

        self.assertEqual(
            self._find_total(results, category=self.rent_category, currency="TRY"),
            Decimal("250.00"),
        )
        self.assertEqual(
            self._find_total(results, category=self.bills_category, currency="TRY"),
            Decimal("75.00"),
        )

    def test_expense_totals_by_category_groups_by_currency(self):
        self._create_category_report_scenario()

        results = self.calculations.calculate_expense_totals_by_category(
            self._transactions(),
        )

        self.assertEqual(
            self._find_total(results, category=self.rent_category, currency="TRY"),
            Decimal("250.00"),
        )
        self.assertEqual(
            self._find_total(results, category=self.rent_category, currency="USD"),
            Decimal("40.00"),
        )

    def test_expense_totals_by_category_returns_empty_when_no_expenses(self):
        self._create_income(
            amount=Decimal("500.00"),
            account=self.try_cash_account,
            category=self.donation_category,
        )
        self._create_transfer()

        results = self.calculations.calculate_expense_totals_by_category(
            self._transactions(),
        )

        self.assertEqual(results, [])

    def test_category_totals_do_not_mix_try_and_usd(self):
        self._create_category_report_scenario()

        income_results = self.calculations.calculate_income_totals_by_category(
            self._transactions(),
        )
        expense_results = self.calculations.calculate_expense_totals_by_category(
            self._transactions(),
        )

        self.assertNotEqual(
            self._find_total(
                income_results,
                category=self.donation_category,
                currency="TRY",
            ),
            Decimal("800.00"),
        )
        self.assertNotEqual(
            self._find_total(expense_results, category=self.rent_category, currency="TRY"),
            Decimal("290.00"),
        )

    def test_category_totals_do_not_mix_try_usd_and_eur(self):
        self._create_category_report_scenario()
        self._create_income(
            amount=Decimal("50.00"),
            account=self.eur_bank_account,
            category=self.donation_category,
        )
        self._create_expense(
            amount=Decimal("10.00"),
            account=self.eur_bank_account,
            category=self.rent_category,
        )
        self._create_transfer(
            amount=Decimal("7.00"),
            source_account=self.eur_bank_account,
            target_account=self.eur_savings_account,
        )

        income_results = self.calculations.calculate_income_totals_by_category(
            self._transactions(),
        )
        expense_results = self.calculations.calculate_expense_totals_by_category(
            self._transactions(),
        )

        self.assertEqual(
            self._find_total(
                income_results,
                category=self.donation_category,
                currency="TRY",
            ),
            Decimal("700.00"),
        )
        self.assertEqual(
            self._find_total(
                income_results,
                category=self.donation_category,
                currency="USD",
            ),
            Decimal("100.00"),
        )
        self.assertEqual(
            self._find_total(
                income_results,
                category=self.donation_category,
                currency="EUR",
            ),
            Decimal("50.00"),
        )
        self.assertNotEqual(
            self._find_total(
                income_results,
                category=self.donation_category,
                currency="TRY",
            ),
            Decimal("850.00"),
        )
        self.assertEqual(
            self._find_total(expense_results, category=self.rent_category, currency="EUR"),
            Decimal("10.00"),
        )

    def test_category_totals_use_given_filtered_transactions_only(self):
        self._create_income(
            amount=Decimal("500.00"),
            account=self.try_cash_account,
            category=self.donation_category,
            transaction_date=date(2026, 6, 1),
        )
        self._create_income(
            amount=Decimal("200.00"),
            account=self.try_cash_account,
            category=self.donation_category,
            transaction_date=date(2026, 6, 15),
        )
        self._create_income(
            amount=Decimal("300.00"),
            account=self.try_cash_account,
            category=self.donation_category,
            transaction_date=date(2026, 7, 1),
        )
        self._create_expense(
            amount=Decimal("75.00"),
            account=self.try_cash_account,
            category=self.bills_category,
            transaction_date=date(2026, 6, 20),
        )

        june_transactions = self.get_transaction_model().objects.filter(
            date__gte=date(2026, 6, 1),
            date__lte=date(2026, 6, 30),
        )

        income_results = self.calculations.calculate_income_totals_by_category(
            june_transactions,
        )
        expense_results = self.calculations.calculate_expense_totals_by_category(
            june_transactions,
        )

        self.assertEqual(
            self._find_total(income_results, category=self.donation_category, currency="TRY"),
            Decimal("700.00"),
        )
        self.assertEqual(
            self._find_total(expense_results, category=self.bills_category, currency="TRY"),
            Decimal("75.00"),
        )
        self.assertNotEqual(
            self._find_total(income_results, category=self.donation_category, currency="TRY"),
            Decimal("1000.00"),
        )
