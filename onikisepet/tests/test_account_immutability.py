from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from onikisepet.models import Account

from .helpers import AccountTestMixin


class AccountOpeningBalanceImmutabilityTests(AccountTestMixin, TestCase):
    def test_account_form_excludes_opening_balance_on_edit(self):
        account = self.create_account(
            name="Immutable Opening Balance",
            opening_balance=Decimal("1000.00"),
        )
        account_form_class = self.get_account_form_class()
        form = account_form_class(instance=account)

        self.assertNotIn("opening_balance", form.fields)

    def test_account_cannot_change_opening_balance_after_create(self):
        account = Account.objects.create(
            name="Immutable Balance Account",
            account_type=Account.AccountType.CASH,
            account_purpose=Account.AccountPurpose.CASH,
            currency=Account.Currency.TRY,
            opening_balance=Decimal("1000.00"),
        )
        account.opening_balance = Decimal("2000.00")

        with self.assertRaises(ValidationError):
            account.save()

    def test_account_create_still_accepts_opening_balance(self):
        account_form_class = self.get_account_form_class()
        form = account_form_class(
            data={
                "name": "New Immutable Account",
                "account_type": "cash",
                "account_purpose": "cash",
                "currency": "TRY",
                "opening_balance": "500.00",
                "is_active": True,
            }
        )

        self.assertTrue(form.is_valid())
