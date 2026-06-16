from decimal import Decimal
from importlib import import_module

from django.test import TestCase

from .helpers import TransactionTestMixin


class CashIncomeFormTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.form_class = self.get_cash_income_form_class()
        self.cash_account = self.create_account(
            name="Kasa",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.bank_account = self.create_account(
            name="Gider Hesabı",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Elden Bağış",
            category_type="income",
        )
        self.expense_category = self.create_category(
            name="Fatura",
            category_type="expense",
        )

    @classmethod
    def get_cash_income_form_class(cls):
        try:
            forms_module = import_module("onikisepet.forms")
        except ModuleNotFoundError as exc:
            raise AssertionError(
                "Create onikisepet.forms module and define CashIncomeForm."
            ) from exc

        try:
            return getattr(forms_module, "CashIncomeForm")
        except AttributeError as exc:
            raise AssertionError(
                "CashIncomeForm must be defined in onikisepet.forms."
            ) from exc

    def build_form_data(self, **overrides):
        data = {
            "date": "2026-06-13",
            "donor_name": "Ahmet Yılmaz",
            "amount": "150.00",
            "cash_account": self.cash_account.pk,
            "category": self.income_category.pk,
            "description": "Pazar bağışı",
        }
        data.update(overrides)
        return data

    def test_form_is_valid_with_required_fields(self):
        form = self.form_class(data=self.build_form_data())

        self.assertTrue(form.is_valid(), form.errors)

    def test_form_maps_donor_name_to_payee(self):
        form = self.form_class(data=self.build_form_data(donor_name="Mehmet Kaya"))

        self.assertTrue(form.is_valid(), form.errors)
        transaction_data = form.get_transaction_data()
        self.assertEqual(transaction_data["payee"], "Mehmet Kaya")

    def test_form_creates_income_transaction_data(self):
        form = self.form_class(data=self.build_form_data())

        self.assertTrue(form.is_valid(), form.errors)
        transaction_data = form.get_transaction_data()
        self.assertEqual(transaction_data["transaction_type"], "income")
        self.assertEqual(transaction_data["target_account"], self.cash_account)
        self.assertIsNone(transaction_data["source_account"])
        self.assertEqual(transaction_data["currency"], "TRY")

    def test_form_rejects_expense_category(self):
        form = self.form_class(
            data=self.build_form_data(category=self.expense_category),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_form_rejects_bank_account(self):
        form = self.form_class(
            data=self.build_form_data(cash_account=self.bank_account),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("cash_account", form.errors)

    def test_form_rejects_negative_amount(self):
        form = self.form_class(data=self.build_form_data(amount="-10.00"))

        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)
