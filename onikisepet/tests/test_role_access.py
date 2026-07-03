from decimal import Decimal
import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import resolve_url
from django.test import TestCase, override_settings
from django.urls import reverse

from onikisepet.models import Receipt

from .helpers import ProfileTestMixin, TransactionTestMixin


class RoleAccessTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    """Bölüm 7: Data Entry işlem girer; Viewer yalnızca rapor ve bakiye görür."""

    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        self.admin_user = self.create_user("role_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "role_data_entry",
            group_name="Data Entry",
        )
        self.viewer_user = self.create_user("role_viewer", group_name="Viewer")
        self.roleless_user = self.create_user("roleless_user")

        self.report_url = reverse("report_dashboard")
        self.home_url = reverse("home")
        self.viewer_allowed_urls = [self.home_url, self.report_url]
        self.viewer_forbidden_urls = [
            reverse("transaction_list"),
            reverse("category_list"),
            reverse("account_list"),
            reverse("cash_income_create"),
            reverse("cash_expense_create"),
            reverse("bank_expense_create"),
            reverse("online_donation_income_create"),
            reverse("transfer_create"),
            reverse("import_new"),
            reverse("category_create"),
            reverse("account_create"),
        ]
        self.data_entry_create_urls = [
            reverse("cash_income_create"),
            reverse("cash_expense_create"),
            reverse("bank_expense_create"),
            reverse("online_donation_income_create"),
            reverse("transfer_create"),
            reverse("import_new"),
        ]
        self.data_entry_operational_urls = [
            reverse("transaction_list"),
            reverse("category_list"),
            reverse("account_list"),
        ]
        self.receipt_download_url = reverse(
            "receipt_download",
            kwargs={"pk": self._create_receipt().pk},
        )

    def _login(self, user):
        self.client.login(username=user.username, password=self.password)

    def _create_receipt(self):
        cash_account = self.create_account(
            name="Role Access Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        expense_category = self.create_category(
            name="Role Access Expense",
            category_type="expense",
        )
        transaction = self.create_transaction(
            transaction_type="expense",
            amount=Decimal("50.00"),
            source_account=cash_account,
            category=expense_category,
            created_by=self.admin_user,
        )
        return Receipt.objects.create(
            transaction=transaction,
            file=SimpleUploadedFile(
                "role-receipt.pdf",
                b"role receipt content",
                content_type="application/pdf",
            ),
            original_filename="role-receipt.pdf",
            uploaded_by=self.admin_user,
        )

    def _assert_urls_return_status(self, urls, expected_status):
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, expected_status)

    def test_viewer_can_access_reports_and_home(self):
        self._login(self.viewer_user)

        self._assert_urls_return_status(self.viewer_allowed_urls, 200)

    def test_viewer_cannot_access_operational_or_create_pages(self):
        self._login(self.viewer_user)

        self._assert_urls_return_status(self.viewer_forbidden_urls, 403)

    def test_viewer_cannot_download_receipts(self):
        self._login(self.viewer_user)

        response = self.client.get(self.receipt_download_url)

        self.assertEqual(response.status_code, 403)

    def test_data_entry_can_access_operational_pages(self):
        self._login(self.data_entry_user)

        self._assert_urls_return_status(self.data_entry_operational_urls, 200)

    def test_data_entry_can_access_create_and_import_pages(self):
        self._login(self.data_entry_user)

        self._assert_urls_return_status(self.data_entry_create_urls, 200)

    def test_data_entry_can_download_receipts(self):
        self._login(self.data_entry_user)

        response = self.client.get(self.receipt_download_url)

        self.assertEqual(response.status_code, 200)

    def test_roleless_user_is_denied_application_access(self):
        self._login(self.roleless_user)

        response = self.client.get(self.home_url)

        self.assertRedirects(
            response,
            reverse("pending_access"),
            fetch_redirect_response=False,
        )

    def test_anonymous_user_is_redirected_to_login(self):
        login_url = resolve_url(settings.LOGIN_URL)

        for url in [self.home_url, self.report_url, reverse("transaction_list")]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f"{login_url}?next={url}",
                    fetch_redirect_response=False,
                )

    def test_viewer_cannot_approve_or_reject_transactions(self):
        cash_account = self.create_account(
            name="Approval Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        income_category = self.create_category(name="Approval Income", category_type="income")
        transaction = self.create_transaction(
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=cash_account,
            category=income_category,
            created_by=self.data_entry_user,
            approval_status="pending",
        )
        approve_url = reverse("transaction_approve", kwargs={"pk": transaction.pk})
        reject_url = reverse("transaction_reject", kwargs={"pk": transaction.pk})

        self._login(self.viewer_user)

        self.assertEqual(self.client.get(approve_url).status_code, 403)
        self.assertEqual(self.client.get(reject_url).status_code, 403)

    def test_data_entry_cannot_approve_or_reject_transactions(self):
        cash_account = self.create_account(
            name="Approval Cash 2",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        income_category = self.create_category(name="Approval Income 2", category_type="income")
        transaction = self.create_transaction(
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=cash_account,
            category=income_category,
            created_by=self.data_entry_user,
            approval_status="pending",
        )
        approve_url = reverse("transaction_approve", kwargs={"pk": transaction.pk})

        self._login(self.data_entry_user)

        self.assertEqual(self.client.get(approve_url).status_code, 403)
