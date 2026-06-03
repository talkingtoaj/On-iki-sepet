from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from .helpers import TransactionTestMixin


class TransactionModelTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("transaction_model_user")
        self.cash_account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.bank_account = self.create_account(
            name="Main Bank Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.usd_account = self.create_account(
            name="USD Account",
            account_type="bank",
            account_purpose="foreign_currency",
            currency="USD",
        )
        self.income_category = self.create_category(
            name="Donation",
            category_type="income",
        )
        self.expense_category = self.create_category(
            name="Rent",
            category_type="expense",
        )

    def test_transaction_can_be_created_as_income(self):
        transaction = self.create_transaction(
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.user,
        )

        self.assertEqual(getattr(transaction, "transaction_type"), "income")

    def test_transaction_can_be_created_as_expense(self):
        transaction = self.create_transaction(
            transaction_type="expense",
            amount=Decimal("75.00"),
            source_account=self.cash_account,
            category=self.expense_category,
            created_by=self.user,
        )

        self.assertEqual(getattr(transaction, "transaction_type"), "expense")

    def test_transaction_can_be_created_as_transfer(self):
        transaction = self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("50.00"),
            source_account=self.cash_account,
            target_account=self.bank_account,
            created_by=self.user,
        )

        self.assertEqual(getattr(transaction, "transaction_type"), "transfer")

    def test_transaction_can_be_created_with_payee(self):
        transaction = self.get_transaction_model()(
            date="2026-05-30",
            transaction_type="expense",
            amount=Decimal("45.00"),
            source_account=self.cash_account,
            category=self.expense_category,
            payee="Migros",
            created_by=self.user,
        )

        transaction.full_clean()
        transaction.save()

        self.assertEqual(transaction.payee, "Migros")

    def test_transaction_payee_is_optional(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="expense",
                amount=Decimal("45.00"),
                source_account=self.cash_account,
                category=self.expense_category,
                created_by=self.user,
            )
        )

        transaction.full_clean()

    def test_existing_income_transaction_is_valid_without_payee(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="income",
                amount=Decimal("100.00"),
                target_account=self.cash_account,
                category=self.income_category,
                created_by=self.user,
            )
        )

        transaction.full_clean()

    def test_existing_expense_transaction_is_valid_without_payee(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="expense",
                amount=Decimal("75.00"),
                source_account=self.cash_account,
                category=self.expense_category,
                created_by=self.user,
            )
        )

        transaction.full_clean()

    def test_existing_transfer_transaction_is_valid_without_payee(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="transfer",
                amount=Decimal("50.00"),
                source_account=self.cash_account,
                target_account=self.bank_account,
                created_by=self.user,
            )
        )

        transaction.full_clean()

    def test_transaction_requires_amount(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                amount=None,
                transaction_type="income",
                target_account=self.cash_account,
                category=self.income_category,
                created_by=self.user,
            )
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_transaction_rejects_zero_amount(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                amount=Decimal("0"),
                transaction_type="income",
                target_account=self.cash_account,
                category=self.income_category,
                created_by=self.user,
            )
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_transaction_rejects_negative_amount(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                amount=Decimal("-1.00"),
                transaction_type="expense",
                source_account=self.cash_account,
                category=self.expense_category,
                created_by=self.user,
            )
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_transaction_requires_valid_transaction_type(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="",
                amount=Decimal("10.00"),
                target_account=self.cash_account,
                category=self.income_category,
                created_by=self.user,
            )
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_transaction_rejects_invalid_transaction_type(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="refund",
                amount=Decimal("10.00"),
                target_account=self.cash_account,
                category=self.income_category,
                created_by=self.user,
            )
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_income_requires_target_account(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="income",
                amount=Decimal("100.00"),
                category=self.income_category,
                created_by=self.user,
            )
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_income_requires_income_category(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="income",
                amount=Decimal("100.00"),
                target_account=self.cash_account,
                category=self.expense_category,
                created_by=self.user,
            )
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_income_does_not_require_source_account(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="income",
                amount=Decimal("100.00"),
                target_account=self.cash_account,
                category=self.income_category,
                created_by=self.user,
            )
        )

        transaction.full_clean()

    def test_expense_requires_source_account(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="expense",
                amount=Decimal("100.00"),
                category=self.expense_category,
                created_by=self.user,
            )
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_expense_requires_expense_category(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="expense",
                amount=Decimal("100.00"),
                source_account=self.cash_account,
                category=self.income_category,
                created_by=self.user,
            )
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_expense_does_not_require_target_account(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="expense",
                amount=Decimal("100.00"),
                source_account=self.cash_account,
                category=self.expense_category,
                created_by=self.user,
            )
        )

        transaction.full_clean()

    def test_transfer_requires_source_account(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="transfer",
                amount=Decimal("100.00"),
                target_account=self.bank_account,
                created_by=self.user,
            )
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_transfer_requires_target_account(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="transfer",
                amount=Decimal("100.00"),
                source_account=self.cash_account,
                created_by=self.user,
            )
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_transfer_does_not_require_category(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="transfer",
                amount=Decimal("100.00"),
                source_account=self.cash_account,
                target_account=self.bank_account,
                created_by=self.user,
            )
        )

        transaction.full_clean()

    def test_transfer_rejects_same_source_account_and_target_account(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="transfer",
                amount=Decimal("100.00"),
                source_account=self.cash_account,
                target_account=self.cash_account,
                created_by=self.user,
            )
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_transfer_rejects_different_source_and_target_currencies_for_mvp(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="transfer",
                amount=Decimal("100.00"),
                source_account=self.cash_account,
                target_account=self.usd_account,
                created_by=self.user,
            )
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_currency_is_derived_from_target_account_for_income(self):
        transaction = self.create_transaction(
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.user,
        )

        self.assertEqual(getattr(transaction, "currency"), "TRY")

    def test_currency_is_derived_from_source_account_for_expense(self):
        transaction = self.create_transaction(
            transaction_type="expense",
            amount=Decimal("100.00"),
            source_account=self.cash_account,
            category=self.expense_category,
            created_by=self.user,
        )

        self.assertEqual(getattr(transaction, "currency"), "TRY")

    def test_currency_is_derived_from_source_account_for_transfer(self):
        transaction = self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("100.00"),
            source_account=self.cash_account,
            target_account=self.bank_account,
            created_by=self.user,
        )

        self.assertEqual(getattr(transaction, "currency"), "TRY")

    def test_str_returns_a_readable_value(self):
        transaction = self.create_transaction(
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.user,
        )

        value = str(transaction)

        self.assertIn("income", value.lower())
        self.assertIn("100", value)
