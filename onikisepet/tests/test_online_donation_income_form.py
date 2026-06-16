from decimal import Decimal
from importlib import import_module

from django.test import TestCase

from .helpers import TransactionTestMixin


class OnlineDonationIncomeFormTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.form_class = self.get_online_donation_income_form_class()
        self.online_donation_account = self.create_account(
            name="Online Donation Bank Account",
            account_type="bank",
            account_purpose="online_donation",
            currency="TRY",
        )
        self.usd_online_donation_account = self.create_account(
            name="USD Online Donation Bank Account",
            account_type="bank",
            account_purpose="online_donation",
            currency="USD",
        )
        self.cash_account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.regular_bank_account = self.create_account(
            name="Main Expense Bank Account",
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
        self.inactive_online_donation_account = self._create_account(
            name="Inactive Online Donation Bank Account",
            account_type="bank",
            account_purpose="online_donation",
            currency="TRY",
            is_active=False,
        )
        self.income_category = self.create_category(
            name="Donation",
            category_type="income",
        )
        self.expense_category = self.create_category(
            name="Bills",
            category_type="expense",
        )
        self.inactive_income_category = self._create_category(
            name="Inactive Donation",
            category_type="income",
            is_active=False,
        )

    @classmethod
    def get_online_donation_income_form_class(cls):
        try:
            forms_module = import_module("onikisepet.forms")
        except ModuleNotFoundError as exc:
            raise AssertionError(
                "Create onikisepet.forms module and define OnlineDonationIncomeForm."
            ) from exc

        try:
            return getattr(forms_module, "OnlineDonationIncomeForm")
        except AttributeError as exc:
            raise AssertionError(
                "OnlineDonationIncomeForm must be defined in onikisepet.forms."
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
        date="2026-06-13",
        donor_name="Jane Donor",
        amount="250.00",
        online_donation_account=None,
        category=None,
        description="Online Sunday donation",
    ):
        data = {
            "date": date,
            "donor_name": donor_name,
            "amount": amount,
            "online_donation_account": str(
                (online_donation_account or self.online_donation_account).pk
            ),
            "category": str((category or self.income_category).pk),
            "description": description,
        }
        return {key: value for key, value in data.items() if value is not None}

    def test_form_is_valid_for_online_donation_income(self):
        form = self.form_class(data=self.build_form_data())

        self.assertTrue(form.is_valid(), form.errors)

    def test_form_requires_donor_name(self):
        form = self.form_class(data=self.build_form_data(donor_name=""))

        self.assertFalse(form.is_valid())
        self.assertIn("donor_name", form.errors)

    def test_form_requires_online_donation_account(self):
        data = self.build_form_data()
        del data["online_donation_account"]

        form = self.form_class(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("online_donation_account", form.errors)

    def test_form_rejects_cash_account(self):
        form = self.form_class(
            data=self.build_form_data(online_donation_account=self.cash_account),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("online_donation_account", form.errors)

    def test_form_rejects_regular_bank_account(self):
        form = self.form_class(
            data=self.build_form_data(
                online_donation_account=self.regular_bank_account,
            ),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("online_donation_account", form.errors)

    def test_form_rejects_savings_account(self):
        form = self.form_class(
            data=self.build_form_data(online_donation_account=self.savings_account),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("online_donation_account", form.errors)

    def test_form_rejects_inactive_online_donation_account(self):
        form = self.form_class(
            data=self.build_form_data(
                online_donation_account=self.inactive_online_donation_account,
            ),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("online_donation_account", form.errors)

    def test_form_requires_income_category(self):
        data = self.build_form_data()
        del data["category"]

        form = self.form_class(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_form_rejects_expense_category(self):
        form = self.form_class(
            data=self.build_form_data(category=self.expense_category),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_form_rejects_inactive_category(self):
        form = self.form_class(
            data=self.build_form_data(category=self.inactive_income_category),
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

    def test_form_does_not_expose_source_account(self):
        form = self.form_class()

        self.assertNotIn("source_account", form.fields)

    def test_form_does_not_expose_target_account(self):
        form = self.form_class()

        self.assertNotIn("target_account", form.fields)

    def test_form_does_not_expose_created_by(self):
        form = self.form_class()

        self.assertNotIn("created_by", form.fields)

    def test_form_creates_income_transaction_data(self):
        form = self.form_class(data=self.build_form_data())

        self.assertTrue(form.is_valid(), form.errors)
        transaction_data = form.get_transaction_data()
        self.assertEqual(transaction_data["transaction_type"], "income")
        self.assertIsNone(transaction_data["source_account"])
        self.assertEqual(
            transaction_data["target_account"],
            self.online_donation_account,
        )
        self.assertEqual(transaction_data["category"], self.income_category)
        self.assertEqual(transaction_data["payee"], "Jane Donor")
        self.assertEqual(transaction_data["amount"], Decimal("250.00"))
        self.assertEqual(transaction_data["currency"], "TRY")
        self.assertEqual(transaction_data["description"], "Online Sunday donation")

    def test_form_uses_online_donation_account_currency(self):
        form = self.form_class(
            data=self.build_form_data(
                online_donation_account=self.usd_online_donation_account,
            ),
        )

        self.assertTrue(form.is_valid(), form.errors)
        transaction_data = form.get_transaction_data()
        self.assertEqual(transaction_data["currency"], "USD")

    def test_form_maps_donor_name_to_payee(self):
        form = self.form_class(data=self.build_form_data(donor_name="Vahan"))

        self.assertTrue(form.is_valid(), form.errors)
        transaction_data = form.get_transaction_data()
        self.assertEqual(transaction_data["payee"], "Vahan")
