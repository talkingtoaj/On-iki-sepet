from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from onikisepet.form_account_defaults import frequent_account_id_for_user
from onikisepet.forms import CashExpenseForm, CashIncomeForm, TransferForm

from .helpers import TransactionTestMixin


class FrequentAccountDefaultTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("frequent_account_user", group_name="Data Entry")
        self.other_user = self.create_user("frequent_account_other", group_name="Data Entry")
        self.primary_cash = self.create_account(
            name="Primary Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.secondary_cash = self.create_account(
            name="Secondary Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.expense_bank = self.create_account(
            name="Expense Bank",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Frequent Income",
            category_type="income",
        )
        self.expense_category = self.create_category(
            name="Frequent Expense",
            category_type="expense",
        )

    def _create_income(self, *, target_account, user=None, amount=Decimal("100.00")):
        return self.create_transaction(
            transaction_type="income",
            amount=amount,
            target_account=target_account,
            category=self.income_category,
            created_by=user or self.user,
            approval_status="approved",
        )

    def _create_expense(self, *, source_account, user=None, amount=Decimal("50.00")):
        return self.create_transaction(
            transaction_type="expense",
            amount=amount,
            source_account=source_account,
            category=self.expense_category,
            created_by=user or self.user,
            approval_status="approved",
        )

    def test_frequent_account_id_uses_most_used_income_target(self):
        self._create_income(target_account=self.secondary_cash)
        self._create_income(target_account=self.primary_cash)
        self._create_income(target_account=self.primary_cash)

        account_id = frequent_account_id_for_user(self.user, "income_target")

        self.assertEqual(account_id, self.primary_cash.pk)

    def test_frequent_account_id_ignores_other_users_transactions(self):
        self._create_income(target_account=self.primary_cash, user=self.other_user)
        self._create_income(target_account=self.secondary_cash)

        account_id = frequent_account_id_for_user(self.user, "income_target")

        self.assertEqual(account_id, self.secondary_cash.pk)

    def test_cash_income_form_defaults_to_frequent_account(self):
        self._create_income(target_account=self.primary_cash)

        form = CashIncomeForm(user=self.user)

        self.assertEqual(form.initial.get("cash_account"), self.primary_cash.pk)

    def test_cash_expense_form_ignores_income_account_usage(self):
        self._create_income(target_account=self.primary_cash)
        self._create_expense(source_account=self.expense_bank)

        form = CashExpenseForm(user=self.user)

        self.assertNotIn("cash_account", form.initial)

    def test_cash_expense_form_defaults_to_frequent_expense_source(self):
        self._create_expense(source_account=self.primary_cash)
        self._create_expense(source_account=self.primary_cash)
        self._create_expense(source_account=self.secondary_cash)

        form = CashExpenseForm(user=self.user)

        self.assertEqual(form.initial.get("cash_account"), self.primary_cash.pk)

    def test_apply_frequent_account_defaults_skips_bound_forms(self):
        self._create_income(target_account=self.primary_cash)

        form = CashIncomeForm(
            data={
                "date": "2026-06-13",
                "donor_name": "Test",
                "amount": "100,00",
                "cash_account": self.secondary_cash.pk,
                "category": self.income_category.pk,
            },
            user=self.user,
        )

        self.assertEqual(form["cash_account"].value(), self.secondary_cash.pk)

    def test_transfer_form_defaults_source_and_target_separately(self):
        self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("200.00"),
            source_account=self.primary_cash,
            target_account=self.expense_bank,
            created_by=self.user,
            approval_status="approved",
        )
        self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("300.00"),
            source_account=self.primary_cash,
            target_account=self.secondary_cash,
            created_by=self.user,
            approval_status="approved",
        )
        self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("400.00"),
            source_account=self.secondary_cash,
            target_account=self.expense_bank,
            created_by=self.user,
            approval_status="approved",
        )

        form = TransferForm(user=self.user)

        self.assertEqual(form.initial.get("source_account"), self.primary_cash.pk)
        self.assertEqual(form.initial.get("target_account"), self.expense_bank.pk)


class FrequentAccountDefaultViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.cash_income_create_url = reverse("cash_income_create")
        self.user = self.create_user("frequent_account_view_user", group_name="Data Entry")
        self.cash_account = self.create_account(
            name="View Default Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="View Default Income",
            category_type="income",
        )

    def test_cash_income_create_page_selects_frequent_account(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("150.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.user,
            approval_status="approved",
        )
        self.client.login(username=self.user.username, password=self.password)

        response = self.client.get(self.cash_income_create_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'<option value="{self.cash_account.pk}" selected',
        )
