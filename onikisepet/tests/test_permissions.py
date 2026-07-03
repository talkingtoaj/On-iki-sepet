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


class PermissionHardeningTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        self.admin_user = self.create_user("permission_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "permission_data_entry",
            group_name="Data Entry",
        )
        self.viewer_user = self.create_user(
            "permission_viewer",
            group_name="Viewer",
        )

        self.cash_account = self.create_account(
            name="Permission Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.expense_category = self.create_category(
            name="Permission Expense",
            category_type="expense",
        )
        self.receipt = self._create_receipt()

        self.setup_create_urls = [
            reverse("category_create"),
            reverse("account_create"),
        ]
        self.transaction_create_urls = [
            reverse("cash_income_create"),
            reverse("cash_expense_create"),
            reverse("bank_expense_create"),
            reverse("online_donation_income_create"),
            reverse("transfer_create"),
            reverse("import_new"),
        ]
        self.viewer_read_only_urls = [
            reverse("home"),
            reverse("report_dashboard"),
        ]
        self.data_entry_read_only_urls = [
            reverse("home"),
            reverse("category_list"),
            reverse("account_list"),
            reverse("transaction_list"),
            reverse("report_dashboard"),
        ]
        self.admin_read_only_urls = [
            reverse("home"),
            reverse("category_list"),
            reverse("account_list"),
            reverse("transaction_list"),
            reverse("report_dashboard"),
        ]
        self.receipt_download_url = reverse(
            "receipt_download",
            kwargs={"pk": self.receipt.pk},
        )

    def _uploaded_file(self):
        return SimpleUploadedFile(
            "permission-receipt.pdf",
            b"permission receipt content",
            content_type="application/pdf",
        )

    def _create_cash_expense_transaction(self):
        return self.get_transaction_model().objects.create(
            date="2026-06-13",
            transaction_type="expense",
            amount=Decimal("75.00"),
            currency="TRY",
            payee="Permission Payee",
            source_account=self.cash_account,
            target_account=None,
            category=self.expense_category,
            description="Permission receipt transaction",
            created_by=self.admin_user,
        )

    def _create_receipt(self):
        return Receipt.objects.create(
            transaction=self._create_cash_expense_transaction(),
            file=self._uploaded_file(),
            original_filename="permission-receipt.pdf",
            uploaded_by=self.admin_user,
        )

    def _login(self, user):
        self.client.login(username=user.username, password=self.password)

    def _assert_urls_return_status(self, urls, expected_status):
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, expected_status)

    def _assert_urls_redirect_to_login(self, urls):
        login_url = resolve_url(settings.LOGIN_URL)

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f"{login_url}?next={url}",
                    fetch_redirect_response=False,
                )

    def test_admin_can_access_setup_create_pages(self):
        self._login(self.admin_user)

        self._assert_urls_return_status(self.setup_create_urls, 200)

    def test_admin_can_access_transaction_create_pages(self):
        self._login(self.admin_user)

        self._assert_urls_return_status(self.transaction_create_urls, 200)

    def test_admin_can_access_read_only_pages(self):
        self._login(self.admin_user)

        self._assert_urls_return_status(self.admin_read_only_urls, 200)

    def test_admin_can_download_receipts(self):
        self._login(self.admin_user)

        response = self.client.get(self.receipt_download_url)

        self.assertEqual(response.status_code, 200)

    def test_data_entry_cannot_access_setup_create_pages(self):
        self._login(self.data_entry_user)

        self._assert_urls_return_status(self.setup_create_urls, 403)

    def test_data_entry_can_access_transaction_create_pages(self):
        self._login(self.data_entry_user)

        self._assert_urls_return_status(self.transaction_create_urls, 200)

    def test_data_entry_can_access_read_only_pages(self):
        self._login(self.data_entry_user)

        self._assert_urls_return_status(self.data_entry_read_only_urls, 200)

    def test_data_entry_can_download_receipts(self):
        self._login(self.data_entry_user)

        response = self.client.get(self.receipt_download_url)

        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_access_setup_create_pages(self):
        self._login(self.viewer_user)

        self._assert_urls_return_status(self.setup_create_urls, 403)

    def test_viewer_cannot_access_transaction_create_pages(self):
        self._login(self.viewer_user)

        self._assert_urls_return_status(self.transaction_create_urls, 403)

    def test_viewer_can_access_report_and_home_pages(self):
        self._login(self.viewer_user)

        self._assert_urls_return_status(self.viewer_read_only_urls, 200)

    def test_viewer_cannot_access_transaction_list(self):
        self._login(self.viewer_user)

        response = self.client.get(reverse("transaction_list"))

        self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_download_receipts(self):
        self._login(self.viewer_user)

        response = self.client.get(self.receipt_download_url)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_from_setup_pages(self):
        self._assert_urls_redirect_to_login(self.setup_create_urls)

    def test_anonymous_user_is_redirected_from_transaction_create_pages(self):
        self._assert_urls_redirect_to_login(self.transaction_create_urls)

    def test_anonymous_user_is_redirected_from_read_only_pages(self):
        self._assert_urls_redirect_to_login(self.admin_read_only_urls)

    def test_anonymous_user_is_redirected_from_receipt_download(self):
        self._assert_urls_redirect_to_login([self.receipt_download_url])
