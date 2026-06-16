from decimal import Decimal
from importlib import import_module

from django.test import TestCase

from .helpers import TransactionTestMixin


class TransferFormTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.form_class = self.get_transfer_form_class()
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
        self.savings_account = self.create_account(
            name="Savings Account",
            account_type="savings",
            account_purpose="savings",
            currency="TRY",
        )
        self.online_donation_account = self.create_account(
            name="Online Donation Account",
            account_type="bank",
            account_purpose="online_donation",
            currency="TRY",
        )
        self.usd_bank_account = self.create_account(
            name="USD Bank Account",
            account_type="bank",
            account_purpose="foreign_currency",
            currency="USD",
        )
        self.inactive_source_account = self._create_account(
            name="Inactive Source Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
            is_active=False,
        )
        self.inactive_target_account = self._create_account(
            name="Inactive Target Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
            is_active=False,
        )

    @classmethod
    def get_transfer_form_class(cls):
        try:
            forms_module = import_module("onikisepet.forms")
        except ModuleNotFoundError as exc:
            raise AssertionError(
                "Create onikisepet.forms module and define TransferForm."
            ) from exc

        try:
            return getattr(forms_module, "TransferForm")
        except AttributeError as exc:
            raise AssertionError(
                "TransferForm must be defined in onikisepet.forms."
            ) from exc

    def _create_account(
        self,
        *,
        name,
        account_type,
        account_purpose,
        currency,
        is_active=True,
    ):
        account_model = self.get_account_model()
        return account_model.objects.create(
            name=name,
            account_type=account_type,
            account_purpose=account_purpose,
            currency=currency,
            is_active=is_active,
        )

    def build_form_data(
        self,
        *,
        date="2026-06-13",
        amount="100.00",
        source_account=None,
        target_account=None,
        description="Move money between church accounts",
    ):
        data = {
            "date": date,
            "amount": amount,
            "source_account": str((source_account or self.cash_account).pk),
            "target_account": str((target_account or self.bank_account).pk),
            "description": description,
        }
        return {key: value for key, value in data.items() if value is not None}

    def test_form_is_valid_for_transfer_between_two_active_accounts(self):
        form = self.form_class(data=self.build_form_data())

        self.assertTrue(form.is_valid(), form.errors)

    def test_form_requires_source_account(self):
        data = self.build_form_data()
        del data["source_account"]

        form = self.form_class(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("source_account", form.errors)

    def test_form_requires_target_account(self):
        data = self.build_form_data()
        del data["target_account"]

        form = self.form_class(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("target_account", form.errors)

    def test_form_rejects_same_source_and_target_account(self):
        form = self.form_class(
            data=self.build_form_data(target_account=self.cash_account),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("target_account", form.errors)

    def test_form_rejects_inactive_source_account(self):
        form = self.form_class(
            data=self.build_form_data(source_account=self.inactive_source_account),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("source_account", form.errors)

    def test_form_rejects_inactive_target_account(self):
        form = self.form_class(
            data=self.build_form_data(target_account=self.inactive_target_account),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("target_account", form.errors)

    def test_form_rejects_zero_amount(self):
        form = self.form_class(data=self.build_form_data(amount="0.00"))

        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_form_rejects_negative_amount(self):
        form = self.form_class(data=self.build_form_data(amount="-1.00"))

        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_form_rejects_cross_currency_transfer(self):
        form = self.form_class(
            data=self.build_form_data(target_account=self.usd_bank_account),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("target_account", form.errors)

    def test_form_allows_online_donation_account_as_source_account(self):
        form = self.form_class(
            data=self.build_form_data(source_account=self.online_donation_account),
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_form_rejects_online_donation_account_as_target_account(self):
        form = self.form_class(
            data=self.build_form_data(target_account=self.online_donation_account),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("target_account", form.errors)

    def test_form_does_not_require_category(self):
        form = self.form_class(data=self.build_form_data())

        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn("category", form.fields)

    def test_form_does_not_require_payee(self):
        form = self.form_class(data=self.build_form_data())

        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn("payee", form.fields)

    def test_form_does_not_require_receipt_file(self):
        form = self.form_class(data=self.build_form_data())

        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn("receipt_file", form.fields)

    def test_form_does_not_expose_transaction_type(self):
        form = self.form_class()

        self.assertNotIn("transaction_type", form.fields)

    def test_form_does_not_expose_currency(self):
        form = self.form_class()

        self.assertNotIn("currency", form.fields)

    def test_form_does_not_expose_created_by(self):
        form = self.form_class()

        self.assertNotIn("created_by", form.fields)

    def test_form_creates_transfer_transaction_data(self):
        form = self.form_class(data=self.build_form_data())

        self.assertTrue(form.is_valid(), form.errors)
        transaction_data = form.get_transaction_data()
        self.assertEqual(transaction_data["date"], form.cleaned_data["date"])
        self.assertEqual(transaction_data["amount"], Decimal("100.00"))
        self.assertEqual(transaction_data["transaction_type"], "transfer")
        self.assertEqual(transaction_data["source_account"], self.cash_account)
        self.assertEqual(transaction_data["target_account"], self.bank_account)
        self.assertIsNone(transaction_data["category"])
        self.assertEqual(transaction_data["payee"], "")
        self.assertEqual(
            transaction_data["description"],
            "Move money between church accounts",
        )

    def test_form_uses_source_account_currency(self):
        form = self.form_class(
            data=self.build_form_data(
                source_account=self.usd_bank_account,
                target_account=self._create_account(
                    name="USD Savings Account",
                    account_type="savings",
                    account_purpose="savings",
                    currency="USD",
                ),
            ),
        )

        self.assertTrue(form.is_valid(), form.errors)
        transaction_data = form.get_transaction_data()
        self.assertEqual(transaction_data["currency"], "USD")

    def test_form_sets_category_to_none(self):
        form = self.form_class(data=self.build_form_data())

        self.assertTrue(form.is_valid(), form.errors)
        transaction_data = form.get_transaction_data()
        self.assertIsNone(transaction_data["category"])

    def test_form_sets_payee_to_empty_string(self):
        form = self.form_class(data=self.build_form_data())

        self.assertTrue(form.is_valid(), form.errors)
        transaction_data = form.get_transaction_data()
        self.assertEqual(transaction_data["payee"], "")
