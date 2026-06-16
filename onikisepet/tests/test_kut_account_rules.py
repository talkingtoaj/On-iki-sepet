from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from onikisepet.kut_accounts import KUT_ACCOUNTS, seed_kut_accounts
from onikisepet.models import Account

from .helpers import TransactionTestMixin


class KutAccountSeedTests(TestCase):
    def test_seed_creates_all_kut_accounts(self):
        created, existing = seed_kut_accounts()

        self.assertEqual(len(created), len(KUT_ACCOUNTS))
        self.assertEqual(existing, [])
        self.assertEqual(Account.objects.count(), len(KUT_ACCOUNTS))

    def test_seed_is_idempotent(self):
        seed_kut_accounts()
        created, existing = seed_kut_accounts()

        self.assertEqual(created, [])
        self.assertEqual(len(existing), len(KUT_ACCOUNTS))
        self.assertEqual(Account.objects.count(), len(KUT_ACCOUNTS))

    def test_seed_includes_online_donation_and_main_expense(self):
        seed_kut_accounts()

        self.assertTrue(
            Account.objects.filter(
                account_purpose=Account.AccountPurpose.ONLINE_DONATION
            ).exists()
        )
        self.assertTrue(
            Account.objects.filter(
                account_purpose=Account.AccountPurpose.MAIN_EXPENSE
            ).exists()
        )


class KutAccountRulesTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.admin_user = self.create_user("kut_rules_admin", is_superuser=True)
        self.income_category = self.create_category(
            name="KUT Bağış",
            category_type="income",
        )
        self.expense_category = self.create_category(
            name="KUT Gider",
            category_type="expense",
        )
        self.online_donation = self.create_account(
            name="KUT Online Bağış",
            account_type="bank",
            account_purpose="online_donation",
            currency="TRY",
        )
        self.main_expense = self.create_account(
            name="KUT Gider Hesabı",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.cash_account = self.create_account(
            name="KUT Kasa",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )

    def test_expense_from_online_donation_account_is_rejected(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="expense",
                amount=Decimal("100.00"),
                source_account=self.online_donation,
                category=self.expense_category,
                created_by=self.admin_user,
            )
        )

        with self.assertRaises(ValidationError) as context:
            transaction.full_clean()

        self.assertIn("source_account", context.exception.error_dict)

    def test_income_to_main_expense_account_is_rejected(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="income",
                amount=Decimal("100.00"),
                target_account=self.main_expense,
                category=self.income_category,
                created_by=self.admin_user,
            )
        )

        with self.assertRaises(ValidationError) as context:
            transaction.full_clean()

        self.assertIn("target_account", context.exception.error_dict)

    def test_transfer_to_online_donation_account_is_rejected(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="transfer",
                amount=Decimal("100.00"),
                source_account=self.cash_account,
                target_account=self.online_donation,
                created_by=self.admin_user,
            )
        )

        with self.assertRaises(ValidationError) as context:
            transaction.full_clean()

        self.assertIn("target_account", context.exception.error_dict)

    def test_transfer_from_online_donation_to_main_expense_is_allowed(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="transfer",
                amount=Decimal("500.00"),
                source_account=self.online_donation,
                target_account=self.main_expense,
                created_by=self.admin_user,
            )
        )

        transaction.full_clean()
        transaction.save()

        self.assertEqual(self.get_transaction_model().objects.count(), 1)

    def test_income_to_online_donation_account_is_allowed(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="income",
                amount=Decimal("250.00"),
                target_account=self.online_donation,
                category=self.income_category,
                created_by=self.admin_user,
            )
        )

        transaction.full_clean()
        transaction.save()

        self.assertEqual(self.get_transaction_model().objects.count(), 1)

    def test_expense_from_main_expense_account_is_allowed(self):
        transaction = self.get_transaction_model()(
            **self.build_transaction_kwargs(
                transaction_type="expense",
                amount=Decimal("75.00"),
                source_account=self.main_expense,
                category=self.expense_category,
                created_by=self.admin_user,
            )
        )

        transaction.full_clean()
        transaction.save()

        self.assertEqual(self.get_transaction_model().objects.count(), 1)
