from decimal import Decimal

from django.test import TestCase

from .helpers import TransactionTestMixin


class CurrencyFinancialCalculationTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("currency_rules_user")
        self.income_category = self.create_category(
            name="Donation",
            category_type="income",
        )
        self.expense_category = self.create_category(
            name="Rent",
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

        self._create_currency_scenario()
        self.calculations = self.get_financial_calculations_module()
        self.transactions = self.get_transaction_model().objects.all()

    def _create_income(self, *, amount, account):
        return self.create_transaction(
            transaction_type="income",
            amount=amount,
            target_account=account,
            category=self.income_category,
            created_by=self.user,
        )

    def _create_expense(self, *, amount, account):
        return self.create_transaction(
            transaction_type="expense",
            amount=amount,
            source_account=account,
            category=self.expense_category,
            created_by=self.user,
        )

    def _create_transfer(self, *, amount, source_account, target_account):
        return self.create_transaction(
            transaction_type="transfer",
            amount=amount,
            source_account=source_account,
            target_account=target_account,
            created_by=self.user,
        )

    def _create_currency_scenario(self):
        self._create_income(amount=Decimal("500.00"), account=self.try_cash_account)
        self._create_expense(amount=Decimal("200.00"), account=self.try_cash_account)
        self._create_transfer(
            amount=Decimal("100.00"),
            source_account=self.try_cash_account,
            target_account=self.try_bank_account,
        )

        self._create_income(amount=Decimal("100.00"), account=self.usd_bank_account)
        self._create_expense(amount=Decimal("25.00"), account=self.usd_bank_account)
        self._create_transfer(
            amount=Decimal("10.00"),
            source_account=self.usd_bank_account,
            target_account=self.usd_savings_account,
        )

        self._create_income(amount=Decimal("50.00"), account=self.eur_bank_account)
        self._create_expense(amount=Decimal("5.00"), account=self.eur_bank_account)
        self._create_transfer(
            amount=Decimal("7.00"),
            source_account=self.eur_bank_account,
            target_account=self.eur_savings_account,
        )

    def test_calculate_income_total_for_try_only_counts_try_income(self):
        total = self.calculations.calculate_income_total_for_currency(
            self.transactions,
            "TRY",
        )

        self.assertEqual(total, Decimal("500.00"))

    def test_calculate_income_total_for_usd_only_counts_usd_income(self):
        total = self.calculations.calculate_income_total_for_currency(
            self.transactions,
            "USD",
        )

        self.assertEqual(total, Decimal("100.00"))

    def test_calculate_income_total_for_eur_only_counts_eur_income(self):
        total = self.calculations.calculate_income_total_for_currency(
            self.transactions,
            "EUR",
        )

        self.assertEqual(total, Decimal("50.00"))

    def test_income_total_by_currency_ignores_expenses_and_transfers(self):
        total = self.calculations.calculate_income_total_for_currency(
            self.transactions,
            "TRY",
        )

        self.assertNotEqual(total, Decimal("800.00"))
        self.assertEqual(total, Decimal("500.00"))

    def test_calculate_expense_total_for_try_only_counts_try_expenses(self):
        total = self.calculations.calculate_expense_total_for_currency(
            self.transactions,
            "TRY",
        )

        self.assertEqual(total, Decimal("200.00"))

    def test_calculate_expense_total_for_usd_only_counts_usd_expenses(self):
        total = self.calculations.calculate_expense_total_for_currency(
            self.transactions,
            "USD",
        )

        self.assertEqual(total, Decimal("25.00"))

    def test_calculate_expense_total_for_eur_only_counts_eur_expenses(self):
        total = self.calculations.calculate_expense_total_for_currency(
            self.transactions,
            "EUR",
        )

        self.assertEqual(total, Decimal("5.00"))

    def test_expense_total_by_currency_ignores_income_and_transfers(self):
        total = self.calculations.calculate_expense_total_for_currency(
            self.transactions,
            "TRY",
        )

        self.assertNotEqual(total, Decimal("800.00"))
        self.assertEqual(total, Decimal("200.00"))

    def test_calculate_net_status_for_try(self):
        total = self.calculations.calculate_net_status_for_currency(
            self.transactions,
            "TRY",
        )

        self.assertEqual(total, Decimal("300.00"))

    def test_calculate_net_status_for_usd(self):
        total = self.calculations.calculate_net_status_for_currency(
            self.transactions,
            "USD",
        )

        self.assertEqual(total, Decimal("75.00"))

    def test_calculate_net_status_for_eur(self):
        total = self.calculations.calculate_net_status_for_currency(
            self.transactions,
            "EUR",
        )

        self.assertEqual(total, Decimal("45.00"))

    def test_net_status_by_currency_ignores_transfers(self):
        total = self.calculations.calculate_net_status_for_currency(
            self.transactions,
            "TRY",
        )

        self.assertNotEqual(total, Decimal("200.00"))
        self.assertEqual(total, Decimal("300.00"))

    def test_build_currency_summary_returns_try_usd_and_eur_sections(self):
        summary = self.calculations.build_currency_summary(self.transactions)

        self.assertEqual(set(summary.keys()), {"TRY", "USD", "EUR"})

    def test_build_currency_summary_does_not_mix_currencies(self):
        summary = self.calculations.build_currency_summary(self.transactions)

        self.assertNotEqual(summary["TRY"]["total_income"], Decimal("650.00"))
        self.assertNotEqual(summary["TRY"]["total_expenses"], Decimal("230.00"))
        self.assertNotEqual(
            summary["TRY"]["net_financial_status"],
            Decimal("420.00"),
        )
        self.assertEqual(summary["TRY"]["total_income"], Decimal("500.00"))
        self.assertEqual(summary["USD"]["total_income"], Decimal("100.00"))
        self.assertEqual(summary["EUR"]["total_income"], Decimal("50.00"))

    def test_build_currency_summary_returns_zero_values_for_missing_currency_transactions(self):
        transactions = self.get_transaction_model().objects.filter(currency="TRY")

        summary = self.calculations.build_currency_summary(transactions)

        self.assertEqual(summary["TRY"]["total_income"], Decimal("500.00"))
        self.assertEqual(summary["USD"]["total_income"], Decimal("0.00"))
        self.assertEqual(summary["USD"]["total_expenses"], Decimal("0.00"))
        self.assertEqual(summary["USD"]["net_financial_status"], Decimal("0.00"))
        self.assertEqual(summary["EUR"]["total_income"], Decimal("0.00"))
        self.assertEqual(summary["EUR"]["total_expenses"], Decimal("0.00"))
        self.assertEqual(summary["EUR"]["net_financial_status"], Decimal("0.00"))
