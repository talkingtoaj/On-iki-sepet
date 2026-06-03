from typing import Any

from django.test import TestCase

from .helpers import TransactionTestMixin


class TransactionFormTests(TransactionTestMixin, TestCase):
    def setUp(self):
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
        self.usd_account = self.create_account(
            name="USD Account",
            account_type="bank",
            account_purpose="foreign_currency",
            currency="USD",
        )
        self.income_category = self.create_category(
            name="Donation",
            category_type="income",
        )
        self.expense_category = self.create_category(
            name="Rent",
            category_type="expense",
        )

    def _build_form_data(
        self,
        *,
        date="2026-05-30",
        amount: str | None = "10.00",
        transaction_type="income",
        account=None,
        source_account=None,
        target_account=None,
        category=None,
        payee=None,
        description="Test transaction",
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
            "date": date,
            "transaction_type": transaction_type,
            "description": description,
        }
        if amount is not None:
            data["amount"] = amount
        if account is not None:
            data["account"] = account.pk
        if source_account is not None:
            data["source_account"] = source_account.pk
        if target_account is not None:
            data["target_account"] = target_account.pk
        if category is not None:
            data["category"] = category.pk
        if payee is not None:
            data["payee"] = payee
        return data

    def test_form_is_valid_for_income_with_date_amount_account_income_category_and_description(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="income",
                account=self.cash_account,
                category=self.income_category,
            )
        )

        self.assertTrue(form.is_valid())

    def test_form_is_valid_for_expense_with_date_amount_account_expense_category_and_description(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="expense",
                account=self.cash_account,
                category=self.expense_category,
            )
        )

        self.assertTrue(form.is_valid())

    def test_form_is_valid_for_transfer_with_date_amount_source_target_and_description(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="transfer",
                source_account=self.cash_account,
                target_account=self.bank_account,
                category=None,
            )
        )

        self.assertTrue(form.is_valid())

    def test_form_is_valid_with_payee(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="expense",
                account=self.cash_account,
                category=self.expense_category,
                payee="Vahan",
            )
        )

        self.assertIn("payee", form.fields)
        self.assertTrue(form.is_valid())

    def test_form_is_valid_without_payee(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="income",
                account=self.cash_account,
                category=self.income_category,
            )
        )

        self.assertTrue(form.is_valid())

    def test_form_saves_payee_value_if_provided(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="expense",
                account=self.cash_account,
                category=self.expense_category,
                payee="Migros",
            )
        )

        self.assertTrue(form.is_valid())
        transaction = form.save(commit=False)

        self.assertEqual(transaction.payee, "Migros")

    def test_form_does_not_require_user_to_manually_provide_currency(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="income",
                account=self.cash_account,
                category=self.income_category,
            )
        )

        self.assertNotIn("currency", form.fields)
        self.assertTrue(form.is_valid())

    def test_form_does_not_allow_user_to_manually_choose_created_by(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="expense",
                account=self.cash_account,
                category=self.expense_category,
            )
        )

        self.assertNotIn("created_by", form.fields)

    def test_form_is_invalid_for_income_without_account(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="income",
                category=self.income_category,
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("account", form.errors)

    def test_form_is_invalid_for_income_without_category(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="income",
                account=self.cash_account,
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_form_is_invalid_for_income_with_expense_category(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="income",
                account=self.cash_account,
                category=self.expense_category,
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_form_is_invalid_for_expense_without_account(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="expense",
                category=self.expense_category,
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("account", form.errors)

    def test_form_is_invalid_for_expense_without_category(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="expense",
                account=self.cash_account,
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_form_is_invalid_for_expense_with_income_category(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="expense",
                account=self.cash_account,
                category=self.income_category,
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_form_is_invalid_for_transfer_without_source_account(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="transfer",
                target_account=self.bank_account,
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("source_account", form.errors)

    def test_form_is_invalid_for_transfer_without_target_account(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="transfer",
                source_account=self.cash_account,
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("target_account", form.errors)

    def test_form_is_invalid_for_transfer_with_same_source_account_and_target_account(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="transfer",
                source_account=self.cash_account,
                target_account=self.cash_account,
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("target_account", form.errors)

    def test_form_is_invalid_for_transfer_with_different_source_and_target_currencies(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="transfer",
                source_account=self.cash_account,
                target_account=self.usd_account,
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("target_account", form.errors)

    def test_form_is_valid_for_transfer_without_category(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="transfer",
                source_account=self.cash_account,
                target_account=self.bank_account,
            )
        )

        self.assertTrue(form.is_valid())

    def test_form_is_invalid_with_zero_amount(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                amount="0",
                transaction_type="income",
                account=self.cash_account,
                category=self.income_category,
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_form_is_invalid_with_negative_amount(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                amount="-1.00",
                transaction_type="expense",
                account=self.cash_account,
                category=self.expense_category,
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_form_is_invalid_with_invalid_transaction_type(self):
        transaction_form_class = self.get_transaction_form_class()
        form = transaction_form_class(
            data=self._build_form_data(
                transaction_type="refund",
                account=self.cash_account,
                category=self.income_category,
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("transaction_type", form.errors)
