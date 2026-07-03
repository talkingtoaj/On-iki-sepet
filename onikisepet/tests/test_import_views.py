from decimal import Decimal

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse

from onikisepet.models import BankStatementImport, BankStatementRow

from .helpers import TransactionTestMixin


class ImportViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.import_new_url = reverse("import_new")
        self.transaction_list_url = reverse("transaction_list")

        self.admin_user = self.create_user("import_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "import_data_entry",
            group_name="Data Entry",
        )
        self.viewer_user = self.create_user("import_viewer", group_name="Viewer")

        self.bank_account = self.create_account(
            name="Main Expense Bank Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.expense_category = self.create_category(
            name="Bank Expense",
            category_type="expense",
        )

    def _csv_file(self):
        content = (
            "date,description,amount,currency,account\n"
            "2026-06-09,Internet bill,325.75,TRY,Main Expense Bank Account\n"
        )
        return SimpleUploadedFile(
            "statement.csv",
            content.encode("utf-8"),
            content_type="text/csv",
        )

    def test_admin_can_access_import_new_page(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.import_new_url)

        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_access_import_new_page(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.import_new_url)

        self.assertEqual(response.status_code, 403)

    def test_upload_redirects_to_preview(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            self.import_new_url,
            data={"file": self._csv_file()},
        )

        bank_import = BankStatementImport.objects.get()
        preview_url = reverse("import_preview", kwargs={"pk": bank_import.pk})

        self.assertRedirects(response, preview_url)
        self.assertEqual(bank_import.rows.count(), 1)

    def test_preview_page_shows_parsed_rows(self):
        bank_import = BankStatementImport.objects.create(
            uploaded_by=self.admin_user,
            original_filename="statement.csv",
        )
        BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=1,
            date="2026-06-09",
            description="Internet bill",
            amount=Decimal("325.75"),
            currency="TRY",
            account=self.bank_account,
        )
        preview_url = reverse("import_preview", kwargs={"pk": bank_import.pk})

        self.client.login(username=self.admin_user.username, password=self.password)
        response = self.client.get(preview_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Internet bill")

    def test_preview_post_redirects_to_confirm(self):
        bank_import = BankStatementImport.objects.create(
            uploaded_by=self.admin_user,
            original_filename="statement.csv",
        )
        row = BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=1,
            date="2026-06-09",
            description="Internet bill",
            amount=Decimal("325.75"),
            currency="TRY",
            account=self.bank_account,
        )
        preview_url = reverse("import_preview", kwargs={"pk": bank_import.pk})
        confirm_url = reverse("import_confirm", kwargs={"pk": bank_import.pk})

        self.client.login(username=self.admin_user.username, password=self.password)
        response = self.client.post(
            preview_url,
            data={
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "1",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                f"form-0-id": row.pk,
                "form-0-transaction_type": "expense",
                "form-0-category": self.expense_category.pk,
                "form-0-target_account": "",
                "form-0-payee": "Internet Provider",
                "form-0-skip_row": "",
            },
        )

        self.assertRedirects(response, confirm_url)

    def test_confirm_post_creates_transactions(self):
        bank_import = BankStatementImport.objects.create(
            uploaded_by=self.admin_user,
            original_filename="statement.csv",
        )
        BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=1,
            date="2026-06-09",
            description="Internet bill",
            amount=Decimal("325.75"),
            currency="TRY",
            account=self.bank_account,
            transaction_type="expense",
            category=self.expense_category,
            payee="Internet Provider",
        )
        confirm_url = reverse("import_confirm", kwargs={"pk": bank_import.pk})

        self.client.login(username=self.admin_user.username, password=self.password)
        response = self.client.post(confirm_url)

        self.assertRedirects(response, self.transaction_list_url)
        self.assertEqual(self.get_transaction_model().objects.count(), 1)
        bank_import.refresh_from_db()
        self.assertEqual(bank_import.status, BankStatementImport.Status.CONFIRMED)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.import_new_url)

        login_url = resolve_url(settings.LOGIN_URL)
        expected_redirect = f"{login_url}?next={self.import_new_url}"
        self.assertRedirects(response, expected_redirect)
