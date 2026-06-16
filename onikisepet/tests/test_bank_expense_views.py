from decimal import Decimal

from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse

from onikisepet.models import Receipt

from .helpers import TransactionTestMixin


class BankExpenseViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.bank_expense_create_url = reverse("bank_expense_create")
        self.transaction_list_url = reverse("transaction_list")

        self.admin_user = self.create_user("bank_expense_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "bank_expense_data_entry",
            group_name="Data Entry",
        )
        self.viewer_user = self.create_user("bank_expense_viewer", group_name="Viewer")

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
        self.expense_category = self.create_category(
            name="Bank Expense",
            category_type="expense",
        )

    def _valid_payload(self, *, bank_account=None):
        return {
            "date": "2026-06-09",
            "payee": "Internet Provider",
            "amount": "325.75",
            "bank_account": (bank_account or self.bank_account).pk,
            "category": self.expense_category.pk,
            "description": "Monthly internet bill paid by EFT",
        }

    def _transaction_model(self):
        return self.get_transaction_model()

    def test_admin_can_access_bank_expense_create_page(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.bank_expense_create_url)

        self.assertEqual(response.status_code, 200)

    def test_data_entry_can_access_bank_expense_create_page(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.bank_expense_create_url)

        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_access_bank_expense_create_page(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.bank_expense_create_url)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.bank_expense_create_url)

        login_url = resolve_url(settings.LOGIN_URL)
        expected_redirect = f"{login_url}?next={self.bank_expense_create_url}"
        self.assertRedirects(
            response,
            expected_redirect,
            fetch_redirect_response=False,
        )

    def test_admin_can_create_bank_expense(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(self.bank_expense_create_url, data=self._valid_payload())

        self.assertEqual(self._transaction_model().objects.count(), 1)
        transaction = self._transaction_model().objects.get()
        self.assertEqual(transaction.transaction_type, "expense")
        self.assertEqual(transaction.source_account, self.bank_account)
        self.assertIsNone(transaction.target_account)
        self.assertEqual(transaction.category, self.expense_category)
        self.assertEqual(transaction.payee, "Internet Provider")
        self.assertEqual(transaction.amount, Decimal("325.75"))
        self.assertEqual(transaction.description, "Monthly internet bill paid by EFT")

    def test_data_entry_can_create_bank_expense(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        self.client.post(self.bank_expense_create_url, data=self._valid_payload())

        self.assertEqual(self._transaction_model().objects.count(), 1)

    def test_bank_expense_create_sets_transaction_created_by(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(self.bank_expense_create_url, data=self._valid_payload())

        transaction = self._transaction_model().objects.get()
        self.assertEqual(transaction.created_by, self.admin_user)

    def test_bank_expense_create_uses_bank_account_currency(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(
            self.bank_expense_create_url,
            data=self._valid_payload(bank_account=self.usd_bank_account),
        )

        transaction = self._transaction_model().objects.get()
        self.assertEqual(transaction.currency, "USD")

    def test_bank_expense_create_does_not_create_receipt(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(self.bank_expense_create_url, data=self._valid_payload())

        self.assertEqual(self._transaction_model().objects.count(), 1)
        self.assertEqual(Receipt.objects.count(), 0)

    def test_successful_bank_expense_create_redirects_to_transaction_list(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            self.bank_expense_create_url,
            data=self._valid_payload(),
        )

        self.assertRedirects(response, self.transaction_list_url)

    def test_invalid_form_does_not_create_transaction(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self._valid_payload()
        payload.pop("bank_account")

        response = self.client.post(self.bank_expense_create_url, data=payload)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "bank_account", "This field is required.")
        self.assertEqual(self._transaction_model().objects.count(), 0)
