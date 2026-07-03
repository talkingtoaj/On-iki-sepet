from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from onikisepet.models import BankStatementImport, BankStatementRow, Transaction

from .helpers import ProfileTestMixin, TransactionTestMixin


class ImportApprovalListUiTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def setUp(self):
        self.data_entry_user = self.create_user_with_profile(
            "import_ui_data_entry",
            role=self.ROLE_DATA_ENTRY,
        )
        self.approver_user = self.create_data_entry_approver("import_ui_approver")
        self.bank_account = self.create_account(
            name="Import UI Bank",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.expense_category = self.create_category(
            name="Import UI Expense",
            category_type="expense",
        )
        self.pending_list_url = reverse("import_list")
        self.account_list_url = reverse("account_list")
        self.category_list_url = reverse("category_list")

    def _create_ready_import(self, *, uploaded_by):
        bank_import = BankStatementImport.objects.create(
            uploaded_by=uploaded_by,
            original_filename="statement.csv",
            status=BankStatementImport.Status.PREVIEW,
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

    def test_approver_sees_pending_import_in_list(self):
        bank_import = self._create_ready_import(uploaded_by=self.data_entry_user)
        self.client.login(username=self.approver_user.username, password=self.password)

        response = self.client.get(self.pending_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, bank_import.original_filename)
        self.assertContains(
            response,
            reverse("import_confirm", kwargs={"pk": bank_import.pk}),
        )

    def test_data_entry_cannot_confirm_import(self):
        bank_import = self._create_ready_import(uploaded_by=self.data_entry_user)
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.post(
            reverse("import_confirm", kwargs={"pk": bank_import.pk}),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_approver_can_view_read_only_import_preview(self):
        bank_import = self._create_ready_import(uploaded_by=self.data_entry_user)
        preview_url = reverse("import_preview", kwargs={"pk": bank_import.pk})
        self.client.login(username=self.approver_user.username, password=self.password)

        response = self.client.get(preview_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Internet bill")
        self.assertContains(response, "325.75")
        self.assertNotContains(response, "Sınıflandırmayı kaydet")

    def test_approver_can_confirm_import_from_list_flow(self):
        bank_import = self._create_ready_import(uploaded_by=self.data_entry_user)
        self.client.login(username=self.approver_user.username, password=self.password)

        response = self.client.post(
            reverse("import_confirm", kwargs={"pk": bank_import.pk}),
        )

        self.assertRedirects(response, reverse("transaction_list"))
        self.assertEqual(Transaction.objects.count(), 1)

    def test_approver_can_view_account_list_read_only(self):
        self.client.login(username=self.approver_user.username, password=self.password)

        response = self.client.get(self.account_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.bank_account.name)
        self.assertNotContains(response, "Hesap Oluştur")

    def test_approver_can_view_category_list_read_only(self):
        self.client.login(username=self.approver_user.username, password=self.password)

        response = self.client.get(self.category_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.expense_category.name)
        self.assertNotContains(response, "Kategori Oluştur")
