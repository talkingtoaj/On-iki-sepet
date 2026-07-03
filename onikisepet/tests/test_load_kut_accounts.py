from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from onikisepet.kut_accounts import KUT_ACCOUNTS
from onikisepet.models import Account

from .helpers import TransactionTestMixin


class LoadKutAccountsCommandTests(TransactionTestMixin, TestCase):
    def test_load_kut_accounts_creates_default_accounts(self):
        call_command("load_kut_accounts")

        self.assertEqual(Account.objects.count(), len(KUT_ACCOUNTS))
        self.assertTrue(
            Account.objects.filter(name="Kasa (Defter)", currency="TRY").exists()
        )
        self.assertTrue(
            Account.objects.filter(
                name="Garanti - Online Bağış",
                account_purpose=Account.AccountPurpose.ONLINE_DONATION,
            ).exists()
        )

    def test_load_kut_accounts_is_idempotent(self):
        call_command("load_kut_accounts")
        call_command("load_kut_accounts")

        self.assertEqual(Account.objects.count(), len(KUT_ACCOUNTS))

    def test_kut_accounts_use_zero_opening_balance_by_default(self):
        call_command("load_kut_accounts")

        for account in Account.objects.all():
            self.assertEqual(account.opening_balance, Decimal("0"))
