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
        self.assertContains(response, "Yükle")
        self.assertContains(response, "Sınıflandır")
        self.assertContains(response, "Onayla")
        self.assertContains(response, "import-wizard")
        self.assertContains(response, reverse("import_sample_csv"))
        self.assertContains(response, "Örnek CSV indir")

    def test_admin_can_download_sample_csv(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(reverse("import_sample_csv"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        content = response.content.decode("utf-8")
        self.assertIn("date,description,amount,currency,account", content)
        self.assertIn("Ornek odeme", content)
        self.assertEqual(len(content.strip().splitlines()), 2)

    def test_viewer_cannot_download_sample_csv(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(reverse("import_sample_csv"))

        self.assertEqual(response.status_code, 403)

    def test_unparseable_pdf_shows_visible_error_on_upload_page(self):
        from unittest.mock import MagicMock, patch

        mock_page = MagicMock()
        mock_page.extract_tables.return_value = []
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]

        self.client.login(username=self.admin_user.username, password=self.password)
        with patch("pdfplumber.open") as mock_pdf_open:
            mock_pdf_open.return_value.__enter__.return_value = mock_pdf
            response = self.client.post(
                self.import_new_url,
                data={
                    "file": SimpleUploadedFile(
                        "statement.pdf",
                        b"%PDF-1.4",
                        content_type="application/pdf",
                    ),
                    "default_account": self.bank_account.pk,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "import-alert")
        self.assertContains(response, "PDF dosyasından tablo okunamadı")
        self.assertContains(response, "Örnek CSV indir")
        self.assertEqual(BankStatementImport.objects.count(), 0)

    def test_missing_csv_columns_shows_error_on_upload_page(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            self.import_new_url,
            data={
                "file": SimpleUploadedFile(
                    "bad.csv",
                    b"date,amount\n2026-06-01,100.00\n",
                    content_type="text/csv",
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "import-alert")
        self.assertContains(response, "gerekli sütunlar eksik")
        self.assertEqual(BankStatementImport.objects.count(), 0)

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
        self.assertContains(response, "import-wizard")
        self.assertContains(response, "Sınıflandır")
        self.assertContains(response, "import-card")
        self.assertContains(response, "import-filters")

    def test_preview_shows_error_banner_and_orders_errors_first(self):
        bank_import = BankStatementImport.objects.create(
            uploaded_by=self.admin_user,
            original_filename="mixed.csv",
        )
        BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=1,
            date="2026-06-09",
            description="Ok row",
            amount=Decimal("10.00"),
            currency="TRY",
            account=self.bank_account,
        )
        BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=2,
            description="Broken row",
            parse_error="Hesap bulunamadı",
        )
        preview_url = reverse("import_preview", kwargs={"pk": bank_import.pk})

        self.client.login(username=self.admin_user.username, password=self.password)
        response = self.client.get(preview_url)
        content = response.content.decode("utf-8")

        self.assertContains(response, "1 satır düzeltilmeli")
        self.assertContains(response, 'data-status="error"')
        self.assertLess(content.index("Broken row"), content.index("Ok row"))

    def test_preview_filter_hides_non_matching_cards(self):
        bank_import = BankStatementImport.objects.create(
            uploaded_by=self.admin_user,
            original_filename="filter.csv",
        )
        BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=1,
            date="2026-06-09",
            description="Pending row",
            amount=Decimal("10.00"),
            currency="TRY",
            account=self.bank_account,
        )
        BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=2,
            date="2026-06-10",
            description="Ready row",
            amount=Decimal("20.00"),
            currency="TRY",
            account=self.bank_account,
            transaction_type="expense",
            category=self.expense_category,
        )
        preview_url = reverse("import_preview", kwargs={"pk": bank_import.pk})

        self.client.login(username=self.admin_user.username, password=self.password)
        response = self.client.get(f"{preview_url}?filter=ready")

        self.assertContains(response, "Ready row")
        self.assertContains(response, "Pending row")
        self.assertContains(response, 'data-status="pending"')
        self.assertRegex(
            response.content.decode("utf-8"),
            r'import-card--pending[^"]*is-filter-hidden',
        )

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

    def test_partial_confirm_redirects_back_to_preview(self):
        bank_import = BankStatementImport.objects.create(
            uploaded_by=self.admin_user,
            original_filename="partial.csv",
        )
        BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=1,
            date="2026-06-09",
            description="Ready",
            amount=Decimal("100.00"),
            currency="TRY",
            account=self.bank_account,
            transaction_type="expense",
            category=self.expense_category,
        )
        BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=2,
            date="2026-06-10",
            description="Later",
            amount=Decimal("50.00"),
            currency="TRY",
            account=self.bank_account,
        )
        confirm_url = reverse("import_confirm", kwargs={"pk": bank_import.pk})
        preview_url = reverse("import_preview", kwargs={"pk": bank_import.pk})

        self.client.login(username=self.admin_user.username, password=self.password)
        response = self.client.post(confirm_url)

        self.assertRedirects(response, preview_url)
        self.assertEqual(self.get_transaction_model().objects.count(), 1)
        bank_import.refresh_from_db()
        self.assertEqual(bank_import.status, BankStatementImport.Status.PREVIEW)

    def test_preview_allows_saving_with_unclassified_rows(self):
        bank_import = BankStatementImport.objects.create(
            uploaded_by=self.admin_user,
            original_filename="later.csv",
        )
        ready = BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=1,
            date="2026-06-09",
            description="Ready",
            amount=Decimal("100.00"),
            currency="TRY",
            account=self.bank_account,
        )
        pending = BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=2,
            date="2026-06-10",
            description="Later",
            amount=Decimal("50.00"),
            currency="TRY",
            account=self.bank_account,
        )
        preview_url = reverse("import_preview", kwargs={"pk": bank_import.pk})
        confirm_url = reverse("import_confirm", kwargs={"pk": bank_import.pk})

        self.client.login(username=self.admin_user.username, password=self.password)
        response = self.client.post(
            preview_url,
            data={
                "form-TOTAL_FORMS": "2",
                "form-INITIAL_FORMS": "2",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-id": ready.pk,
                "form-0-transaction_type": "expense",
                "form-0-category": self.expense_category.pk,
                "form-0-target_account": "",
                "form-0-payee": "",
                "form-0-skip_row": "",
                "form-1-id": pending.pk,
                "form-1-transaction_type": "",
                "form-1-category": "",
                "form-1-target_account": "",
                "form-1-payee": "",
                "form-1-skip_row": "",
            },
        )

        self.assertRedirects(response, confirm_url)
        ready.refresh_from_db()
        pending.refresh_from_db()
        self.assertEqual(ready.transaction_type, "expense")
        self.assertEqual(ready.category_id, self.expense_category.pk)
        self.assertEqual(pending.transaction_type, "")
        self.assertIsNone(pending.category_id)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.import_new_url)

        login_url = resolve_url(settings.LOGIN_URL)
        expected_redirect = f"{login_url}?next={self.import_new_url}"
        self.assertRedirects(response, expected_redirect)
