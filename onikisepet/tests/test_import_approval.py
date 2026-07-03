from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from onikisepet.models import BankStatementImport, BankStatementRow, Transaction

from .helpers import ProfileTestMixin, TransactionTestMixin


class ImportApprovalTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def setUp(self):
        self.data_entry_user = self.create_user_with_profile(
            "import_approval_data_entry",
            role=self.ROLE_DATA_ENTRY,
        )
        self.approver_user = self.create_data_entry_approver("import_approval_approver")
        self.bank_account = self.create_account(
            name="Import Approval Bank",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.expense_category = self.create_category(
            name="Import Approval Expense",
            category_type="expense",
        )

    def _create_ready_import(self, *, uploaded_by):
        bank_import = BankStatementImport.objects.create(
            uploaded_by=uploaded_by,
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
        return bank_import

    def test_data_entry_cannot_confirm_import(self):
        bank_import = self._create_ready_import(uploaded_by=self.data_entry_user)
        confirm_url = reverse("import_confirm", kwargs={"pk": bank_import.pk})
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.post(confirm_url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_approver_can_confirm_import_after_preview(self):
        bank_import = self._create_ready_import(uploaded_by=self.data_entry_user)
        confirm_url = reverse("import_confirm", kwargs={"pk": bank_import.pk})
        self.client.login(username=self.approver_user.username, password=self.password)

        response = self.client.post(confirm_url)

        self.assertRedirects(response, reverse("transaction_list"))
        self.assertEqual(Transaction.objects.count(), 1)
        bank_import.refresh_from_db()
        self.assertEqual(bank_import.status, BankStatementImport.Status.CONFIRMED)

    def test_data_entry_can_upload_and_preview_import(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)
        content = (
            "date,description,amount,currency,account\n"
            "2026-06-09,Internet bill,325.75,TRY,Import Approval Bank\n"
        )
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = self.client.post(
            reverse("import_new"),
            data={
                "file": SimpleUploadedFile(
                    "statement.csv",
                    content.encode("utf-8"),
                    content_type="text/csv",
                )
            },
        )

        bank_import = BankStatementImport.objects.get()
        preview_url = reverse("import_preview", kwargs={"pk": bank_import.pk})
        self.assertRedirects(response, preview_url)
