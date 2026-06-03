from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from .helpers import AccountTestMixin


class AccountModelTests(AccountTestMixin, TestCase):
    def test_account_can_be_created_with_cash_type(self):
        account = self.create_account(
            name="Cash Box",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )

        self.assertEqual(getattr(account, "account_type"), "cash")

    def test_account_can_be_created_with_bank_type(self):
        account = self.create_account(
            name="Donation Bank",
            account_type="bank",
            account_purpose="online_donation",
            currency="TRY",
        )

        self.assertEqual(getattr(account, "account_type"), "bank")

    def test_account_can_be_created_with_savings_type(self):
        account = self.create_account(
            name="Savings Vault",
            account_type="savings",
            account_purpose="savings",
            currency="TRY",
        )

        self.assertEqual(getattr(account, "account_type"), "savings")

    def test_account_can_be_created_with_cash_purpose(self):
        account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )

        self.assertEqual(getattr(account, "account_purpose"), "cash")

    def test_account_can_be_created_with_online_donation_purpose(self):
        account = self.create_account(
            name="Online Donation Account",
            account_type="bank",
            account_purpose="online_donation",
            currency="TRY",
        )

        self.assertEqual(getattr(account, "account_purpose"), "online_donation")

    def test_account_can_be_created_with_main_expense_purpose(self):
        account = self.create_account(
            name="Main Expense Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )

        self.assertEqual(getattr(account, "account_purpose"), "main_expense")

    def test_account_can_be_created_with_foreign_currency_purpose(self):
        account = self.create_account(
            name="USD Foreign Account",
            account_type="bank",
            account_purpose="foreign_currency",
            currency="USD",
        )

        self.assertEqual(getattr(account, "account_purpose"), "foreign_currency")

    def test_account_can_be_created_with_savings_purpose(self):
        account = self.create_account(
            name="Savings Account",
            account_type="savings",
            account_purpose="savings",
            currency="TRY",
        )

        self.assertEqual(getattr(account, "account_purpose"), "savings")

    def test_account_can_be_created_with_try_currency(self):
        account = self.create_account(
            name="TRY Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )

        self.assertEqual(getattr(account, "currency"), "TRY")

    def test_account_can_be_created_with_usd_currency(self):
        account = self.create_account(
            name="USD Account",
            account_type="bank",
            account_purpose="foreign_currency",
            currency="USD",
        )

        self.assertEqual(getattr(account, "currency"), "USD")

    def test_account_can_be_created_with_eur_currency(self):
        account = self.create_account(
            name="EUR Account",
            account_type="bank",
            account_purpose="foreign_currency",
            currency="EUR",
        )

        self.assertEqual(getattr(account, "currency"), "EUR")

    def test_account_requires_a_name(self):
        account_model = self.get_account_model()
        account = account_model(
            **self.build_account_kwargs(
                name="",
                account_type="cash",
                account_purpose="cash",
                currency="TRY",
            )
        )

        with self.assertRaises(ValidationError):
            account.full_clean()

    def test_account_name_must_be_unique(self):
        self.create_account(
            name="Main Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        duplicate = self.get_account_model()(
            **self.build_account_kwargs(
                name="Main Account",
                account_type="bank",
                account_purpose="main_expense",
                currency="TRY",
            )
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_account_requires_a_valid_account_type(self):
        account_model = self.get_account_model()
        account = account_model(
            **self.build_account_kwargs(
                name="Type Required",
                account_type="",
                account_purpose="cash",
                currency="TRY",
            )
        )

        with self.assertRaises(ValidationError):
            account.full_clean()

    def test_account_rejects_invalid_account_type(self):
        account_model = self.get_account_model()
        account = account_model(
            **self.build_account_kwargs(
                name="Invalid Type Account",
                account_type="wallet",
                account_purpose="cash",
                currency="TRY",
            )
        )

        with self.assertRaises(ValidationError):
            account.full_clean()

    def test_account_requires_a_valid_account_purpose(self):
        account_model = self.get_account_model()
        account = account_model(
            **self.build_account_kwargs(
                name="Purpose Required",
                account_type="bank",
                account_purpose="",
                currency="TRY",
            )
        )

        with self.assertRaises(ValidationError):
            account.full_clean()

    def test_account_rejects_invalid_account_purpose(self):
        account_model = self.get_account_model()
        account = account_model(
            **self.build_account_kwargs(
                name="Invalid Purpose Account",
                account_type="bank",
                account_purpose="transfer",
                currency="TRY",
            )
        )

        with self.assertRaises(ValidationError):
            account.full_clean()

    def test_account_requires_a_valid_currency(self):
        account_model = self.get_account_model()
        account = account_model(
            **self.build_account_kwargs(
                name="Currency Required",
                account_type="bank",
                account_purpose="main_expense",
                currency="",
            )
        )

        with self.assertRaises(ValidationError):
            account.full_clean()

    def test_account_rejects_invalid_currency(self):
        account_model = self.get_account_model()
        account = account_model(
            **self.build_account_kwargs(
                name="Invalid Currency Account",
                account_type="bank",
                account_purpose="foreign_currency",
                currency="GBP",
            )
        )

        with self.assertRaises(ValidationError):
            account.full_clean()

    def test_account_is_active_by_default(self):
        account = self.create_account(
            name="Default Active Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )

        self.assertTrue(getattr(account, "is_active"))

    def test_account_opening_balance_defaults_to_zero(self):
        account = self.create_account(
            name="Zero Default Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )

        self.assertEqual(getattr(account, "opening_balance"), Decimal("0"))

    def test_account_can_be_created_with_opening_balance(self):
        account = self.create_account(
            name="Cash With Opening Balance",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
            opening_balance=Decimal("2500.00"),
        )

        self.assertEqual(getattr(account, "opening_balance"), Decimal("2500.00"))

    def test_account_can_be_created_with_zero_opening_balance(self):
        account = self.create_account(
            name="Online Donation With Zero Opening Balance",
            account_type="bank",
            account_purpose="online_donation",
            currency="TRY",
            opening_balance=Decimal("0"),
        )

        self.assertEqual(getattr(account, "opening_balance"), Decimal("0"))

    def test_account_rejects_negative_opening_balance(self):
        account_model = self.get_account_model()
        account = account_model(
            **self.build_account_kwargs(
                name="Negative Opening Balance Account",
                account_type="bank",
                account_purpose="main_expense",
                currency="TRY",
                opening_balance=Decimal("-1.00"),
            )
        )

        with self.assertRaises(ValidationError):
            account.full_clean()

    def test_inactive_accounts_are_stored_but_marked_inactive(self):
        account = self.create_account(
            name="Inactive Account",
            account_type="savings",
            account_purpose="savings",
            currency="TRY",
            is_active=False,
        )

        self.assertTrue(self.get_account_model().objects.filter(pk=account.pk).exists())
        self.assertFalse(getattr(account, "is_active"))

    def test_str_returns_the_account_name(self):
        account = self.create_account(
            name="Main Cash Box",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )

        self.assertEqual(str(account), "Main Cash Box")
