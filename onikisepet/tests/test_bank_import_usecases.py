import io
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from onikisepet.models import BankStatementImport, BankStatementRow
from onikisepet.usecases import bank_import as bank_import_ops

from .helpers import TransactionTestMixin


class BankImportUsecaseTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("import_user", is_superuser=True)
        self.bank_account = self.create_account(
            name="Main Expense Bank Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.income_bank_account = self.create_account(
            name="Online Donation Account",
            account_type="bank",
            account_purpose="online_donation",
            currency="TRY",
        )
        self.cash_account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.expense_category = self.create_category(
            name="Bank Expense",
            category_type="expense",
        )
        self.income_category = self.create_category(
            name="Donation",
            category_type="income",
        )

    def _csv_file(self, content, name="statement.csv"):
        return SimpleUploadedFile(
            name,
            content.encode("utf-8"),
            content_type="text/csv",
        )

    def test_create_import_from_csv_parses_rows(self):
        csv_content = (
            "date,description,amount,currency,account\n"
            "2026-06-01,Market alışverişi,125.50,TRY,Main Expense Bank Account\n"
            "2026-06-02,EFT geliri,500.00,TRY,Main Expense Bank Account\n"
        )
        uploaded_file = self._csv_file(csv_content)

        bank_import = bank_import_ops.create_import_from_upload(
            uploaded_file,
            self.user,
        )

        self.assertEqual(bank_import.status, BankStatementImport.Status.PREVIEW)
        self.assertEqual(bank_import.rows.count(), 2)
        first_row = bank_import.rows.get(row_number=1)
        self.assertEqual(first_row.date.isoformat(), "2026-06-01")
        self.assertEqual(first_row.description, "Market alışverişi")
        self.assertEqual(first_row.amount, Decimal("125.50"))
        self.assertEqual(first_row.currency, "TRY")
        self.assertEqual(first_row.account, self.bank_account)
        self.assertEqual(first_row.parse_error, "")

    def test_create_import_rejects_missing_columns(self):
        uploaded_file = self._csv_file("date,amount\n2026-06-01,100.00\n")

        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            bank_import_ops.create_import_from_upload(uploaded_file, self.user)

    def test_create_import_marks_unknown_account_as_error(self):
        csv_content = (
            "date,description,amount,currency,account\n"
            "2026-06-01,Test,100.00,TRY,Unknown Account\n"
        )
        uploaded_file = self._csv_file(csv_content)

        bank_import = bank_import_ops.create_import_from_upload(
            uploaded_file,
            self.user,
        )

        row = bank_import.rows.get()
        self.assertIn("Hesap bulunamadı", row.parse_error)

    def test_confirm_import_creates_transactions(self):
        bank_import = BankStatementImport.objects.create(
            uploaded_by=self.user,
            original_filename="manual.csv",
            status=BankStatementImport.Status.PREVIEW,
        )
        BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=1,
            date="2026-06-01",
            description="Internet bill",
            amount=Decimal("325.75"),
            currency="TRY",
            account=self.bank_account,
            transaction_type="expense",
            category=self.expense_category,
        )
        BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=2,
            date="2026-06-02",
            description="Donation",
            amount=Decimal("500.00"),
            currency="TRY",
            account=self.income_bank_account,
            transaction_type="income",
            category=self.income_category,
        )

        bank_import_ops.confirm_import(bank_import, self.user)

        bank_import.refresh_from_db()
        self.assertEqual(bank_import.status, BankStatementImport.Status.CONFIRMED)
        self.assertEqual(self.get_transaction_model().objects.count(), 2)

        expense_row = bank_import.rows.get(row_number=1)
        self.assertEqual(expense_row.transaction.transaction_type, "expense")
        self.assertEqual(expense_row.transaction.source_account, self.bank_account)

        income_row = bank_import.rows.get(row_number=2)
        self.assertEqual(income_row.transaction.transaction_type, "income")
        self.assertEqual(income_row.transaction.target_account, self.income_bank_account)

    def test_confirm_import_creates_transfer_transaction(self):
        bank_import = BankStatementImport.objects.create(
            uploaded_by=self.user,
            original_filename="transfer.csv",
            status=BankStatementImport.Status.PREVIEW,
        )
        BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=1,
            date="2026-06-03",
            description="Cash top-up",
            amount=Decimal("1000.00"),
            currency="TRY",
            account=self.bank_account,
            transaction_type="transfer",
            target_account=self.cash_account,
        )

        bank_import_ops.confirm_import(bank_import, self.user)

        row = bank_import.rows.get()
        self.assertEqual(row.transaction.transaction_type, "transfer")
        self.assertEqual(row.transaction.source_account, self.bank_account)
        self.assertEqual(row.transaction.target_account, self.cash_account)
        self.assertEqual(
            row.transaction.approval_status,
            self.get_transaction_model().ApprovalStatus.PENDING,
        )

    def test_confirm_import_skips_marked_rows(self):
        bank_import = BankStatementImport.objects.create(
            uploaded_by=self.user,
            original_filename="skip.csv",
            status=BankStatementImport.Status.PREVIEW,
        )
        BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=1,
            date="2026-06-01",
            description="Skip me",
            amount=Decimal("10.00"),
            currency="TRY",
            account=self.bank_account,
            is_skipped=True,
        )
        BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=2,
            date="2026-06-02",
            description="Keep me",
            amount=Decimal("20.00"),
            currency="TRY",
            account=self.bank_account,
            transaction_type="expense",
            category=self.expense_category,
        )

        bank_import_ops.confirm_import(bank_import, self.user)

        self.assertEqual(self.get_transaction_model().objects.count(), 1)

    def test_confirm_import_saves_ready_rows_and_leaves_incomplete(self):
        bank_import = BankStatementImport.objects.create(
            uploaded_by=self.user,
            original_filename="partial.csv",
            status=BankStatementImport.Status.PREVIEW,
        )
        BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=1,
            date="2026-06-01",
            description="Ready expense",
            amount=Decimal("100.00"),
            currency="TRY",
            account=self.bank_account,
            transaction_type="expense",
            category=self.expense_category,
        )
        BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=2,
            date="2026-06-02",
            description="Later",
            amount=Decimal("50.00"),
            currency="TRY",
            account=self.bank_account,
        )

        result = bank_import_ops.confirm_import(bank_import, self.user)

        bank_import.refresh_from_db()
        self.assertEqual(result.imported_count, 1)
        self.assertEqual(result.pending_count, 1)
        self.assertEqual(bank_import.status, BankStatementImport.Status.PREVIEW)
        self.assertEqual(self.get_transaction_model().objects.count(), 1)
        self.assertIsNotNone(bank_import.rows.get(row_number=1).transaction_id)
        self.assertIsNone(bank_import.rows.get(row_number=2).transaction_id)

    def test_confirm_import_again_imports_newly_ready_rows(self):
        bank_import = BankStatementImport.objects.create(
            uploaded_by=self.user,
            original_filename="partial2.csv",
            status=BankStatementImport.Status.PREVIEW,
        )
        ready = BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=1,
            date="2026-06-01",
            description="First",
            amount=Decimal("100.00"),
            currency="TRY",
            account=self.bank_account,
            transaction_type="expense",
            category=self.expense_category,
        )
        later = BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=2,
            date="2026-06-02",
            description="Second",
            amount=Decimal("50.00"),
            currency="TRY",
            account=self.bank_account,
        )

        bank_import_ops.confirm_import(bank_import, self.user)

        later.transaction_type = "expense"
        later.category = self.expense_category
        later.save(update_fields=["transaction_type", "category"])

        result = bank_import_ops.confirm_import(bank_import, self.user)

        bank_import.refresh_from_db()
        ready.refresh_from_db()
        later.refresh_from_db()
        self.assertEqual(result.imported_count, 1)
        self.assertEqual(result.pending_count, 0)
        self.assertEqual(bank_import.status, BankStatementImport.Status.CONFIRMED)
        self.assertEqual(self.get_transaction_model().objects.count(), 2)
        self.assertIsNotNone(later.transaction_id)
        self.assertNotEqual(ready.transaction_id, later.transaction_id)

    def test_online_donation_account_rows_get_default_classification(self):
        from onikisepet.models import Category

        online_category, _ = Category.objects.get_or_create(
            name="Online Bağış",
            defaults={
                "category_type": Category.CategoryType.INCOME,
                "is_active": True,
            },
        )
        csv_content = (
            "date,description,amount,currency,account\n"
            "2026-06-01,Online donor,250.00,TRY,Online Donation Account\n"
            "2026-06-02,Shop,80.00,TRY,Main Expense Bank Account\n"
        )
        uploaded_file = self._csv_file(csv_content)

        bank_import = bank_import_ops.create_import_from_upload(
            uploaded_file,
            self.user,
        )

        donation_row = bank_import.rows.get(row_number=1)
        self.assertEqual(donation_row.transaction_type, "income")
        self.assertEqual(donation_row.category, online_category)

        expense_row = bank_import.rows.get(row_number=2)
        self.assertEqual(expense_row.transaction_type, "")
        self.assertIsNone(expense_row.category_id)

    def test_parse_amount_supports_turkish_decimal_format(self):
        amount = bank_import_ops.parse_amount_value("1.234,56")
        self.assertEqual(amount, Decimal("1234.56"))

    def test_build_sample_csv_content_includes_required_columns(self):
        content = bank_import_ops.build_sample_csv_content(
            account_name="Main Expense Bank Account",
        )

        self.assertIn("date,description,amount,currency,account", content)
        self.assertIn("Main Expense Bank Account", content)
        self.assertIn("125.50", content)

    def test_order_rows_for_preview_puts_errors_first(self):
        bank_import = BankStatementImport.objects.create(
            uploaded_by=self.user,
            original_filename="order.csv",
        )
        pending = BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=1,
            date="2026-06-01",
            description="Pending",
            amount=Decimal("10.00"),
            currency="TRY",
            account=self.bank_account,
        )
        error = BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=2,
            description="Error",
            parse_error="bad",
        )
        ready = BankStatementRow.objects.create(
            bank_statement_import=bank_import,
            row_number=3,
            date="2026-06-03",
            description="Ready",
            amount=Decimal("20.00"),
            currency="TRY",
            account=self.bank_account,
            transaction_type="expense",
            category=self.expense_category,
        )

        ordered = bank_import_ops.order_rows_for_preview([pending, error, ready])

        self.assertEqual(
            [row.pk for row in ordered],
            [error.pk, pending.pk, ready.pk],
        )

    def test_parse_amount_strips_tl_suffix(self):
        amount = bank_import_ops.parse_amount_value("-1.200,00 TL")
        self.assertEqual(amount, Decimal("1200.00"))

    def test_enpara_table_format_parses_with_default_account(self):
        table = [
            ["Tarih", "Hareket tipi", "Açıklama", "İşlem Tutarı", "Bakiye"],
            [
                "24.06.2026",
                "Giden Transfer",
                "James Martin Gran,",
                "-1.200,00 TL",
                "67.798,70 TL",
            ],
        ]
        rows = bank_import_ops.rows_from_table(
            table,
            default_account=self.bank_account,
        )
        accounts_by_name = bank_import_ops.build_accounts_lookup()
        parsed = bank_import_ops.parse_row_values(
            rows[0],
            row_number=1,
            accounts_by_name=accounts_by_name,
        )

        self.assertEqual(parsed["parse_error"], "")
        self.assertEqual(parsed["date"].isoformat(), "2026-06-24")
        self.assertEqual(parsed["amount"], Decimal("1200.00"))
        self.assertEqual(parsed["currency"], "TRY")
        self.assertEqual(parsed["account"], self.bank_account)
        self.assertEqual(parsed["description"], "Giden Transfer — James Martin Gran,")

    @patch("pdfplumber.open")
    def test_create_import_from_pdf_parses_table_rows(self, mock_pdf_open):
        mock_page = MagicMock()
        mock_page.extract_tables.return_value = [
            [
                ["date", "description", "amount", "currency", "account"],
                [
                    "2026-06-01",
                    "Market alışverişi",
                    "125.50",
                    "TRY",
                    "Main Expense Bank Account",
                ],
            ],
        ]
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        uploaded_file = SimpleUploadedFile(
            "statement.pdf",
            b"%PDF-1.4",
            content_type="application/pdf",
        )

        bank_import = bank_import_ops.create_import_from_upload(
            uploaded_file,
            self.user,
            default_account=self.bank_account,
        )

        self.assertEqual(bank_import.rows.count(), 1)
        row = bank_import.rows.get()
        self.assertEqual(row.description, "Market alışverişi")
        self.assertEqual(row.parse_error, "")

    @patch("pdfplumber.open")
    def test_create_import_from_pdf_rejects_unparseable_file(self, mock_pdf_open):
        mock_page = MagicMock()
        mock_page.extract_tables.return_value = []
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        uploaded_file = SimpleUploadedFile(
            "statement.pdf",
            b"%PDF-1.4",
            content_type="application/pdf",
        )

        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            bank_import_ops.create_import_from_upload(
                uploaded_file,
                self.user,
                default_account=self.bank_account,
            )
