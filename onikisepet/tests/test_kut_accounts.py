from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from onikisepet.kut_accounts import KUT_ACCOUNTS, load_kut_accounts
from onikisepet.models import Account


class KutAccountsTests(TestCase):
    def test_kut_accounts_spec_defines_eight_accounts(self):
        self.assertEqual(len(KUT_ACCOUNTS), 8)

    def test_load_kut_accounts_creates_all_accounts_on_first_run(self):
        created_count = load_kut_accounts()

        self.assertEqual(created_count, 8)
        self.assertEqual(Account.objects.count(), 8)

    def test_load_kut_accounts_is_idempotent(self):
        load_kut_accounts()

        created_count = load_kut_accounts()

        self.assertEqual(created_count, 0)
        self.assertEqual(Account.objects.count(), 8)

    def test_load_kut_accounts_sets_expected_fields(self):
        load_kut_accounts()

        for spec in KUT_ACCOUNTS:
            with self.subTest(name=spec["name"]):
                account = Account.objects.get(name=spec["name"])
                self.assertEqual(account.account_type, spec["account_type"])
                self.assertEqual(account.account_purpose, spec["account_purpose"])
                self.assertEqual(account.currency, spec["currency"])
                self.assertEqual(account.opening_balance, spec["opening_balance"])
                self.assertTrue(account.is_active)

    def test_load_kut_accounts_does_not_overwrite_existing_account_fields(self):
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
        self.assertEqual(created_count, 7)
        self.assertEqual(account.account_type, Account.AccountType.BANK)
        self.assertEqual(account.account_purpose, Account.AccountPurpose.MAIN_EXPENSE)
        self.assertEqual(account.currency, Account.Currency.USD)
        self.assertEqual(account.opening_balance, Decimal("999.00"))
        self.assertFalse(account.is_active)


class LoadKutAccountsCommandTests(TestCase):
    def test_command_creates_accounts_and_reports_created_count(self):
        stdout = StringIO()

        call_command("load_kut_accounts", stdout=stdout)

        self.assertEqual(Account.objects.count(), 8)
        self.assertIn("Oluşturulan hesap sayısı: 8", stdout.getvalue())

    def test_command_reports_existing_accounts_on_second_run(self):
        load_kut_accounts()
        stdout = StringIO()

        call_command("load_kut_accounts", stdout=stdout)

        self.assertIn("Zaten mevcut hesap sayısı: 8", stdout.getvalue())
        self.assertNotIn("Oluşturulan hesap sayısı:", stdout.getvalue())
