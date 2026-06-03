from decimal import Decimal

from django.test import TestCase

from .helpers import TransactionTestMixin


class TransactionBusinessRuleTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("transaction_rules_user")
        self.cash_account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
            opening_balance=Decimal("1000.00"),
        )
        self.bank_account = self.create_account(
            name="Bank Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
            opening_balance=Decimal("500.00"),
        )
        self.income_category = self.create_category(
            name="Donation",
            category_type="income",
        )
        self.expense_category = self.create_category(
            name="Rent",
            category_type="expense",
        )

    def _create_income(self, amount=Decimal("100.00"), account=None):
        return self.create_transaction(
            transaction_type="income",
            amount=amount,
            target_account=account or self.cash_account,
            category=self.income_category,
            created_by=self.user,
        )

    def _create_expense(self, amount=Decimal("40.00"), account=None):
        return self.create_transaction(
            transaction_type="expense",
            amount=amount,
            source_account=account or self.cash_account,
            category=self.expense_category,
            created_by=self.user,
        )

    def _create_transfer(
        self,
        amount=Decimal("25.00"),
        source_account=None,
        target_account=None,
    ):
        return self.create_transaction(
            transaction_type="transfer",
            amount=amount,
            source_account=source_account or self.cash_account,
            target_account=target_account or self.bank_account,
            created_by=self.user,
        )

    def test_income_transactions_are_counted_as_income(self):
        income = self._create_income(amount=Decimal("100.00"))
        calculations = self.get_financial_calculations_module()

        total = calculations.calculate_income_total([income])

        self.assertEqual(total, Decimal("100.00"))

    def test_expense_transactions_are_counted_as_expenses(self):
        expense = self._create_expense(amount=Decimal("40.00"))
        calculations = self.get_financial_calculations_module()

        total = calculations.calculate_expense_total([expense])

        self.assertEqual(total, Decimal("40.00"))

    def test_transfer_transactions_are_not_counted_as_income(self):
        transfer = self._create_transfer(amount=Decimal("25.00"))
        calculations = self.get_financial_calculations_module()

        total = calculations.calculate_income_total([transfer])

        self.assertEqual(total, Decimal("0"))

    def test_transfer_transactions_are_not_counted_as_expenses(self):
        transfer = self._create_transfer(amount=Decimal("25.00"))
        calculations = self.get_financial_calculations_module()

        total = calculations.calculate_expense_total([transfer])

        self.assertEqual(total, Decimal("0"))

    def test_transfer_transactions_stay_separate_from_income_and_expense_totals(self):
        transfer = self._create_transfer(amount=Decimal("25.00"))
        calculations = self.get_financial_calculations_module()

        total = calculations.calculate_transfer_total([transfer])

        self.assertEqual(total, Decimal("25.00"))

    def test_income_total_ignores_transfers(self):
        income = self._create_income(amount=Decimal("100.00"))
        transfer = self._create_transfer(amount=Decimal("25.00"))
        calculations = self.get_financial_calculations_module()

        total = calculations.calculate_income_total([income, transfer])

        self.assertEqual(total, Decimal("100.00"))

    def test_expense_total_ignores_transfers(self):
        expense = self._create_expense(amount=Decimal("40.00"))
        transfer = self._create_transfer(amount=Decimal("25.00"))
        calculations = self.get_financial_calculations_module()

        total = calculations.calculate_expense_total([expense, transfer])

        self.assertEqual(total, Decimal("40.00"))

    def test_account_balance_calculation_starts_from_opening_balance(self):
        calculations = self.get_financial_calculations_module()

        balance = calculations.calculate_account_balance(self.cash_account)

        self.assertEqual(balance, Decimal("1000.00"))

    def test_income_increases_the_target_account_balance(self):
        self._create_income(amount=Decimal("100.00"), account=self.cash_account)
        calculations = self.get_financial_calculations_module()

        balance = calculations.calculate_account_balance(self.cash_account)

        self.assertEqual(balance, Decimal("1100.00"))

    def test_expense_decreases_the_source_account_balance(self):
        self._create_expense(amount=Decimal("40.00"), account=self.cash_account)
        calculations = self.get_financial_calculations_module()

        balance = calculations.calculate_account_balance(self.cash_account)

        self.assertEqual(balance, Decimal("960.00"))

    def test_transfer_decreases_the_source_account_balance(self):
        self._create_transfer(
            amount=Decimal("25.00"),
            source_account=self.cash_account,
            target_account=self.bank_account,
        )
        calculations = self.get_financial_calculations_module()

        balance = calculations.calculate_account_balance(self.cash_account)

        self.assertEqual(balance, Decimal("975.00"))

    def test_transfer_increases_the_target_account_balance(self):
        self._create_transfer(
            amount=Decimal("25.00"),
            source_account=self.cash_account,
            target_account=self.bank_account,
        )
        calculations = self.get_financial_calculations_module()

        balance = calculations.calculate_account_balance(self.bank_account)

        self.assertEqual(balance, Decimal("525.00"))

    def test_transfer_does_not_change_total_net_financial_position(self):
        self._create_transfer(
            amount=Decimal("25.00"),
            source_account=self.cash_account,
            target_account=self.bank_account,
        )
        calculations = self.get_financial_calculations_module()

        total = calculations.calculate_total_net_position(
            [self.cash_account, self.bank_account]
        )

        self.assertEqual(total, Decimal("1500.00"))
