from decimal import Decimal
from typing import Any

from django.test import TestCase

from .helpers import AccountTestMixin


class AccountFormTests(AccountTestMixin, TestCase):
    def _build_form_data(
        self,
        *,
        name="Cash Account",
        account_type="cash",
        account_purpose="cash",
        currency="TRY",
        is_active=True,
        opening_balance=None,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": name,
            "account_type": account_type,
            "account_purpose": account_purpose,
            "currency": currency,
            "is_active": is_active,
        }
        if opening_balance is not None:
            data["opening_balance"] = opening_balance
        return data

    def test_form_is_valid_with_name_type_purpose_currency_and_is_active(self):
        account_form_class = self.get_account_form_class()
        form = account_form_class(
            data=self._build_form_data(
                name="Online Donation Account",
                account_type="bank",
                account_purpose="online_donation",
                currency="TRY",
                is_active=True,
            )
        )

        self.assertTrue(form.is_valid())

    def test_form_is_invalid_without_name(self):
        account_form_class = self.get_account_form_class()
        form = account_form_class(
            data=self._build_form_data(
                name="",
                account_type="cash",
                account_purpose="cash",
                currency="TRY",
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_form_is_invalid_without_account_type(self):
        account_form_class = self.get_account_form_class()
        data = self._build_form_data(
            name="Missing Type Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        data.pop("account_type")
        form = account_form_class(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("account_type", form.errors)

    def test_form_is_invalid_with_invalid_account_type(self):
        account_form_class = self.get_account_form_class()
        form = account_form_class(
            data=self._build_form_data(
                name="Invalid Type",
                account_type="wallet",
                account_purpose="cash",
                currency="TRY",
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("account_type", form.errors)

    def test_form_is_invalid_without_account_purpose(self):
        account_form_class = self.get_account_form_class()
        data = self._build_form_data(
            name="Missing Purpose Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        data.pop("account_purpose")
        form = account_form_class(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("account_purpose", form.errors)

    def test_form_is_invalid_with_invalid_account_purpose(self):
        account_form_class = self.get_account_form_class()
        form = account_form_class(
            data=self._build_form_data(
                name="Invalid Purpose",
                account_type="bank",
                account_purpose="transfer",
                currency="TRY",
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("account_purpose", form.errors)

    def test_form_is_invalid_without_currency(self):
        account_form_class = self.get_account_form_class()
        data = self._build_form_data(
            name="Missing Currency Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        data.pop("currency")
        form = account_form_class(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("currency", form.errors)

    def test_form_is_invalid_with_invalid_currency(self):
        account_form_class = self.get_account_form_class()
        form = account_form_class(
            data=self._build_form_data(
                name="Invalid Currency",
                account_type="bank",
                account_purpose="foreign_currency",
                currency="GBP",
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("currency", form.errors)

    def test_form_is_invalid_with_duplicate_account_name(self):
        self.create_account(
            name="Main Expense Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        account_form_class = self.get_account_form_class()
        form = account_form_class(
            data=self._build_form_data(
                name="Main Expense Account",
                account_type="bank",
                account_purpose="main_expense",
                currency="TRY",
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_form_is_valid_with_opening_balance(self):
        account_form_class = self.get_account_form_class()
        form = account_form_class(
            data=self._build_form_data(
                name="Cash With Opening Balance",
                account_type="cash",
                account_purpose="cash",
                currency="TRY",
                opening_balance=Decimal("2500.00"),
            )
        )

        self.assertIn("opening_balance", form.fields)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["opening_balance"], Decimal("2500.00"))

    def test_form_is_valid_with_zero_opening_balance(self):
        account_form_class = self.get_account_form_class()
        form = account_form_class(
            data=self._build_form_data(
                name="Online Donation With Zero Opening Balance",
                account_type="bank",
                account_purpose="online_donation",
                currency="TRY",
                opening_balance=Decimal("0"),
            )
        )

        self.assertIn("opening_balance", form.fields)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["opening_balance"], Decimal("0"))

    def test_form_is_invalid_with_negative_opening_balance(self):
        account_form_class = self.get_account_form_class()
        form = account_form_class(
            data=self._build_form_data(
                name="Negative Opening Balance",
                account_type="bank",
                account_purpose="main_expense",
                currency="TRY",
                opening_balance=Decimal("-1.00"),
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("opening_balance", form.errors)
