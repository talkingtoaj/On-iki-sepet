from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from onikisepet import messages as msg
from onikisepet.account_rules import (
    transfer_source_accounts,
    transfer_target_accounts,
    validate_account_purpose_for_transaction,
)
from onikisepet.models import Transaction

from .helpers import TransactionTestMixin


class TransferAccountQuerysetTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.cash_account = self.create_account(
            name="Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.online_donation_account = self.create_account(
            name="Online Donation",
            account_type="bank",
            account_purpose="online_donation",
            currency="TRY",
        )
        self.main_expense_account = self.create_account(
            name="Main Expense",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )

    def test_transfer_source_accounts_includes_active_operational_accounts(self):
        source_ids = set(transfer_source_accounts().values_list("pk", flat=True))

        self.assertEqual(
            source_ids,
            {
                self.cash_account.pk,
                self.online_donation_account.pk,
                self.main_expense_account.pk,
            },
        )

    def test_transfer_target_accounts_excludes_online_donation_accounts(self):
        target_ids = set(transfer_target_accounts().values_list("pk", flat=True))

        self.assertIn(self.cash_account.pk, target_ids)
        self.assertIn(self.main_expense_account.pk, target_ids)
        self.assertNotIn(self.online_donation_account.pk, target_ids)


class ValidateAccountPurposeTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("account_rules_user")
        self.cash_account = self.create_account(
            name="Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.online_donation_account = self.create_account(
            name="Online Donation",
            account_type="bank",
            account_purpose="online_donation",
            currency="TRY",
        )
        self.main_expense_account = self.create_account(
            name="Main Expense",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Donation",
            category_type="income",
        )
        self.expense_category = self.create_category(
            name="Rent",
            category_type="expense",
        )

    def test_income_to_main_expense_account_is_forbidden(self):
        transaction = Transaction(
            date="2026-06-15",
            transaction_type=Transaction.TransactionType.INCOME,
            amount=Decimal("100.00"),
            target_account=self.main_expense_account,
            category=self.income_category,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as exc:
            transaction.full_clean()

        self.assertIn(msg.INCOME_TO_EXPENSE_ACCOUNT_FORBIDDEN, str(exc.exception))

    def test_expense_from_online_donation_account_is_forbidden(self):
        transaction = Transaction(
            date="2026-06-15",
            transaction_type=Transaction.TransactionType.EXPENSE,
            amount=Decimal("50.00"),
            source_account=self.online_donation_account,
            category=self.expense_category,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as exc:
            transaction.full_clean()

        self.assertIn(msg.EXPENSE_FROM_ONLINE_DONATION_FORBIDDEN, str(exc.exception))

    def test_transfer_to_online_donation_account_is_forbidden(self):
        transaction = Transaction(
            date="2026-06-15",
            transaction_type=Transaction.TransactionType.TRANSFER,
            amount=Decimal("25.00"),
            source_account=self.cash_account,
            target_account=self.online_donation_account,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as exc:
            transaction.full_clean()

        self.assertIn(msg.TRANSFER_TO_ONLINE_DONATION_FORBIDDEN, str(exc.exception))

    def test_valid_income_to_cash_account_passes_account_purpose_rules(self):
        transaction = Transaction(
            date="2026-06-15",
            transaction_type=Transaction.TransactionType.INCOME,
            amount=Decimal("100.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.user,
        )

        errors: dict[str, str] = {}
        validate_account_purpose_for_transaction(transaction, errors)

        self.assertEqual(errors, {})

    def test_valid_transfer_to_main_expense_account_passes_account_purpose_rules(self):
        transaction = Transaction(
            date="2026-06-15",
            transaction_type=Transaction.TransactionType.TRANSFER,
            amount=Decimal("25.00"),
            source_account=self.online_donation_account,
            target_account=self.main_expense_account,
            created_by=self.user,
        )

        errors: dict[str, str] = {}
        validate_account_purpose_for_transaction(transaction, errors)

        self.assertEqual(errors, {})
