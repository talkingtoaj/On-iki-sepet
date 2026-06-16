from decimal import Decimal
from importlib import import_module

from django.test import TestCase

from .helpers import TransactionTestMixin


class BankExpenseFormTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.form_class = self.get_bank_expense_form_class()
        self.bank_account = self.create_account(
            name="Main Expense Bank Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.usd_bank_account = self.create_account(
            name="USD Main Expense Bank Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="USD",
        )
        self.cash_account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.online_donation_account = self.create_account(
            name="Online Donation Bank Account",
            account_type="bank",
            account_purpose="online_donation",
            currency="TRY",
        )
        self.inactive_bank_account = self._create_account(
            name="Inactive Bank Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
            is_active=False,
        )
        self.expense_category = self.create_category(
            name="Bills",
            category_type="expense",
        )
        self.income_category = self.create_category(
            name="Donation",
            category_type="income",
        )
        self.inactive_expense_category = self._create_category(
            name="Inactive Expense",
            category_type="expense",
            is_active=False,
        )

    @classmethod
    def get_bank_expense_form_class(cls):
        try:
            forms_module = import_module("onikisepet.forms")
        except ModuleNotFoundError as exc:
            raise AssertionError(
                "Create onikisepet.forms module and define BankExpenseForm."
            ) from exc

        try:
            return getattr(forms_module, "BankExpenseForm")
        except AttributeError as exc:
            raise AssertionError(
                "BankExpenseForm must be defined in onikisepet.forms."
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

    def _create_category(self, *, name, category_type, is_active=True):
        category_model = self.get_category_model()
        return category_model.objects.create(
            name=name,
            category_type=category_type,
            is_active=is_active,
        )

    def build_form_data(
        self,
        *,
        date="2026-06-09",
        payee="Electric Company",
        amount="125.50",
        bank_account=None,
        category=None,
        description="Monthly bill payment",
    ):
        data = {
            "date": date,
            "payee": payee,
            "amount": amount,
            "bank_account": str((bank_account or self.bank_account).pk),
            "category": str((category or self.expense_category).pk),
            "description": description,
        }
        return {key: value for key, value in data.items() if value is not None}

    def test_form_is_valid_for_bank_expense(self):
        form = self.form_class(data=self.build_form_data())

        self.assertTrue(form.is_valid(), form.errors)

    def test_form_requires_payee(self):
        form = self.form_class(data=self.build_form_data(payee=""))

        self.assertFalse(form.is_valid())
        self.assertIn("payee", form.errors)

    def test_form_requires_bank_account(self):
        data = self.build_form_data()
        del data["bank_account"]

        form = self.form_class(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("bank_account", form.errors)

    def test_form_rejects_cash_account(self):
        form = self.form_class(
            data=self.build_form_data(bank_account=self.cash_account),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("bank_account", form.errors)

    def test_form_rejects_online_donation_account(self):
        form = self.form_class(
            data=self.build_form_data(bank_account=self.online_donation_account),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("bank_account", form.errors)

    def test_form_rejects_inactive_bank_account(self):
        form = self.form_class(
            data=self.build_form_data(bank_account=self.inactive_bank_account),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("bank_account", form.errors)

    def test_form_requires_expense_category(self):
        data = self.build_form_data()
        del data["category"]

        form = self.form_class(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_form_rejects_income_category(self):
        form = self.form_class(
            data=self.build_form_data(category=self.income_category),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_form_rejects_inactive_category(self):
        form = self.form_class(
            data=self.build_form_data(category=self.inactive_expense_category),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_form_rejects_zero_amount(self):
        form = self.form_class(data=self.build_form_data(amount="0.00"))

        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_form_rejects_negative_amount(self):
        form = self.form_class(data=self.build_form_data(amount="-1.00"))

        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

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

    def test_form_creates_expense_transaction_data(self):
        form = self.form_class(data=self.build_form_data())

        self.assertTrue(form.is_valid(), form.errors)
        transaction_data = form.get_transaction_data()
        self.assertEqual(transaction_data["transaction_type"], "expense")
        self.assertEqual(transaction_data["source_account"], self.bank_account)
        self.assertIsNone(transaction_data["target_account"])
        self.assertEqual(transaction_data["category"], self.expense_category)
        self.assertEqual(transaction_data["payee"], "Electric Company")
        self.assertEqual(transaction_data["amount"], Decimal("125.50"))
        self.assertEqual(transaction_data["currency"], "TRY")
        self.assertEqual(transaction_data["description"], "Monthly bill payment")

    def test_form_uses_bank_account_currency(self):
        form = self.form_class(
            data=self.build_form_data(bank_account=self.usd_bank_account),
        )

        self.assertTrue(form.is_valid(), form.errors)
        transaction_data = form.get_transaction_data()
        self.assertEqual(transaction_data["currency"], "USD")
