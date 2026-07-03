from decimal import Decimal
import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import resolve_url
from django.test import TestCase, override_settings
from django.urls import reverse

from onikisepet.models import Receipt

from .helpers import TransactionTestMixin


class ReceiptDownloadViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        self.admin_user = self.create_user("receipt_download_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "receipt_download_data_entry",
            group_name="Data Entry",
        )
        self.viewer_user = self.create_user(
            "receipt_download_viewer",
            group_name="Viewer",
        )
        self.cash_account = self.create_account(
            name="Receipt Download Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.expense_category = self.create_category(
            name="Receipt Download Expense",
            category_type="expense",
        )
        self.receipt = self._create_receipt()
        self.receipt_download_url = reverse(
            "receipt_download",
            kwargs={"pk": self.receipt.pk},
        )

    def _uploaded_file(self, name="migros-receipt.pdf", content=b"receipt bytes"):
        return SimpleUploadedFile(
            name,
            content,
            content_type="application/pdf",
        )

    def _create_cash_expense_transaction(self):
        return self.get_transaction_model().objects.create(
            date="2026-06-13",
            transaction_type="expense",
            amount=Decimal("125.50"),
            currency="TRY",
            payee="Migros",
            source_account=self.cash_account,
            target_account=None,
            category=self.expense_category,
            description="Cash grocery reimbursement",
            created_by=self.admin_user,
        )

    def _create_receipt(self):
        return Receipt.objects.create(
            transaction=self._create_cash_expense_transaction(),
            file=self._uploaded_file(),
            original_filename="migros-receipt.pdf",
            uploaded_by=self.admin_user,
        )

    def _response_content(self, response):
        if response.streaming:
            return b"".join(response.streaming_content)
        return response.content

    def _login_admin(self):
        self.client.login(username=self.admin_user.username, password=self.password)

    def test_admin_can_download_receipt(self):
        self._login_admin()

        response = self.client.get(self.receipt_download_url)

        self.assertEqual(response.status_code, 200)

    def test_data_entry_can_download_receipt(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.receipt_download_url)

        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_download_receipt(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.receipt_download_url)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.receipt_download_url)

        login_url = resolve_url(settings.LOGIN_URL)
        expected_redirect = f"{login_url}?next={self.receipt_download_url}"
        self.assertRedirects(
            response,
            expected_redirect,
            fetch_redirect_response=False,
        )

    def test_missing_receipt_returns_404(self):
        self._login_admin()
        missing_receipt_url = reverse("receipt_download", kwargs={"pk": 999999})

        response = self.client.get(missing_receipt_url)

        self.assertEqual(response.status_code, 404)

    def test_receipt_download_returns_file_content(self):
        self._login_admin()

        response = self.client.get(self.receipt_download_url)

        self.assertEqual(self._response_content(response), b"receipt bytes")

    def test_receipt_download_includes_filename(self):
        self._login_admin()

        response = self.client.get(self.receipt_download_url)

        content_disposition = response.headers.get("Content-Disposition", "")
        self.assertIn("migros-receipt.pdf", content_disposition)

    def test_receipt_download_does_not_create_transaction(self):
        self._login_admin()
        transaction_count = self.get_transaction_model().objects.count()

        self.client.get(self.receipt_download_url)

        self.assertEqual(
            self.get_transaction_model().objects.count(),
            transaction_count,
        )

    def test_receipt_download_does_not_create_receipt(self):
        self._login_admin()
        receipt_count = Receipt.objects.count()

        self.client.get(self.receipt_download_url)

        self.assertEqual(Receipt.objects.count(), receipt_count)
