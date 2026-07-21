from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from onikisepet.kut_accounts import KUT_ACCOUNTS, load_kut_accounts
from onikisepet.models import Account


class KutAccountsTests(TestCase):
    def test_kut_accounts_spec_defines_eight_accounts(self):
        self.assertEqual(len(KUT_ACCOUNTS), 8)

    def test_seed_migration_loads_kut_accounts_in_test_database(self):
        self.assertEqual(Account.objects.count(), len(KUT_ACCOUNTS))

    def test_load_kut_accounts_is_idempotent_after_seed(self):
        created_count = load_kut_accounts()

        self.assertEqual(created_count, 0)
        self.assertEqual(Account.objects.count(), len(KUT_ACCOUNTS))

    def test_load_kut_accounts_sets_expected_fields(self):
        for spec in KUT_ACCOUNTS:
            with self.subTest(name=spec["name"]):
                account = Account.objects.get(name=spec["name"])
                self.assertEqual(account.account_type, spec["account_type"])
                self.assertEqual(account.account_purpose, spec["account_purpose"])
                self.assertEqual(account.currency, spec["currency"])
                self.assertEqual(account.opening_balance, spec["opening_balance"])
                self.assertTrue(account.is_active)

    def test_load_kut_accounts_does_not_overwrite_existing_account_fields(self):
        Account.objects.all().delete()
        Account.objects.create(
            name="Kasa (Defter)",
            account_type=Account.AccountType.BANK,
            account_purpose=Account.AccountPurpose.MAIN_EXPENSE,
            currency=Account.Currency.USD,
            opening_balance=Decimal("999.00"),
            is_active=False,
        )

        created_count = load_kut_accounts()

        account = Account.objects.get(name="Kasa (Defter)")
        self.assertEqual(created_count, len(KUT_ACCOUNTS) - 1)
        self.assertEqual(account.account_type, Account.AccountType.BANK)
        self.assertEqual(account.account_purpose, Account.AccountPurpose.MAIN_EXPENSE)
        self.assertEqual(account.currency, Account.Currency.USD)
        self.assertEqual(account.opening_balance, Decimal("999.00"))
        self.assertFalse(account.is_active)


class LoadKutAccountsCommandTests(TestCase):
    def test_command_reports_seed_accounts_when_already_loaded(self):
        self.assertEqual(Account.objects.count(), len(KUT_ACCOUNTS))
        stdout = StringIO()

        call_command("load_kut_accounts", stdout=stdout)

        self.assertIn(
            f"Zaten mevcut hesap sayısı: {len(KUT_ACCOUNTS)}",
            stdout.getvalue(),
        )

    def test_command_reports_existing_accounts_on_second_run(self):
        load_kut_accounts()
        stdout = StringIO()

        call_command("load_kut_accounts", stdout=stdout)

        self.assertIn(
            f"Zaten mevcut hesap sayısı: {len(KUT_ACCOUNTS)}",
            stdout.getvalue(),
        )
        self.assertNotIn("Oluşturulan hesap sayısı:", stdout.getvalue())
