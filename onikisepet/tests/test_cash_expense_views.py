from decimal import Decimal

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse

from onikisepet.models import Receipt

from .helpers import TransactionTestMixin


class CashExpenseViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.cash_expense_create_url = reverse("cash_expense_create")
        self.transaction_list_url = reverse("transaction_list")

        self.admin_user = self.create_user("cash_expense_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "cash_expense_data_entry",
            group_name="Data Entry",
        )
        self.viewer_user = self.create_user("cash_expense_viewer", group_name="Viewer")

        self.cash_account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.expense_category = self.create_category(
            name="Cash Expense",
            category_type="expense",
        )

    def _uploaded_file(self, name="receipt.jpg"):
        return SimpleUploadedFile(
            name,
            b"fake receipt content",
            content_type="image/jpeg",
        )

    def _valid_payload(self, *, receipt_name="receipt.jpg"):
        return {
            "date": "2026-06-03",
            "payee": "Migros",
            "amount": "125.50",
            "cash_account": self.cash_account.pk,
            "category": self.expense_category.pk,
            "description": "Cash grocery reimbursement",
            "receipt_file": self._uploaded_file(receipt_name),
        }

    def _transaction_model(self):
        return self.get_transaction_model()

    def test_admin_can_access_cash_expense_create_page(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.cash_expense_create_url)

        self.assertEqual(response.status_code, 200)

    def test_data_entry_can_access_cash_expense_create_page(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.cash_expense_create_url)

        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_access_cash_expense_create_page(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.cash_expense_create_url)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.cash_expense_create_url)

        login_url = resolve_url(settings.LOGIN_URL)
        expected_redirect = f"{login_url}?next={self.cash_expense_create_url}"
        self.assertRedirects(
            response,
            expected_redirect,
            fetch_redirect_response=False,
        )

    def test_admin_can_create_cash_expense_with_receipt(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(self.cash_expense_create_url, data=self._valid_payload())

        self.assertEqual(self._transaction_model().objects.count(), 1)
        self.assertEqual(Receipt.objects.count(), 1)
        transaction = self._transaction_model().objects.get()
        self.assertEqual(transaction.transaction_type, "expense")
        self.assertEqual(transaction.source_account, self.cash_account)
        self.assertIsNone(transaction.target_account)
        self.assertEqual(transaction.category, self.expense_category)
        self.assertEqual(transaction.payee, "Migros")
        self.assertEqual(transaction.amount, Decimal("125.50"))
        self.assertEqual(transaction.description, "Cash grocery reimbursement")

    def test_data_entry_can_create_cash_expense_with_receipt(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        self.client.post(self.cash_expense_create_url, data=self._valid_payload())

        self.assertEqual(self._transaction_model().objects.count(), 1)
        self.assertEqual(Receipt.objects.count(), 1)

    def test_cash_expense_create_sets_transaction_created_by(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(self.cash_expense_create_url, data=self._valid_payload())

        transaction = self._transaction_model().objects.get()
        self.assertEqual(transaction.created_by, self.admin_user)

    def test_cash_expense_create_sets_receipt_uploaded_by(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        self.client.post(self.cash_expense_create_url, data=self._valid_payload())

        receipt = Receipt.objects.get()
        self.assertEqual(receipt.uploaded_by, self.data_entry_user)

    def test_cash_expense_create_saves_original_filename(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(
            self.cash_expense_create_url,
            data=self._valid_payload(receipt_name="migros-bill.jpg"),
        )

        receipt = Receipt.objects.get()
        self.assertEqual(receipt.original_filename, "migros-bill.jpg")

    def test_cash_expense_create_sets_receipt_file_type(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(
            self.cash_expense_create_url,
            data=self._valid_payload(receipt_name="migros-bill.pdf"),
        )

        receipt = Receipt.objects.get()
        self.assertEqual(receipt.file_type, "pdf")

    def test_cash_expense_create_uses_cash_account_currency(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(self.cash_expense_create_url, data=self._valid_payload())

        transaction = self._transaction_model().objects.get()
        self.assertEqual(transaction.currency, "TRY")

    def test_successful_cash_expense_create_redirects(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            self.cash_expense_create_url,
            data=self._valid_payload(),
        )

        self.assertRedirects(response, self.transaction_list_url)

    def test_invalid_form_does_not_create_transaction_or_receipt(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self._valid_payload()
        payload.pop("receipt_file")

        response = self.client.post(self.cash_expense_create_url, data=payload)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "receipt_file", "Bu alan zorunludur.")
        self.assertEqual(self._transaction_model().objects.count(), 0)
        self.assertEqual(Receipt.objects.count(), 0)
