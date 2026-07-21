from decimal import Decimal

from django.test import TestCase

from onikisepet.forms import BankStatementRowClassificationForm
from onikisepet.models import BankStatementImport, BankStatementRow

from .helpers import TransactionTestMixin


class BankStatementRowClassificationFormTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("row_form_user", is_superuser=True)
        self.bank_account = self.create_account(
            name="Form Bank",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.expense_category = self.create_category(
            name="Form Expense",
            category_type="expense",
        )
        self.bank_import = BankStatementImport.objects.create(
            uploaded_by=self.user,
            original_filename="form.csv",
        )
        self.row = BankStatementRow.objects.create(
            bank_statement_import=self.bank_import,
            row_number=1,
            date="2026-06-01",
            description="Unclassified",
            amount=Decimal("10.00"),
            currency="TRY",
            account=self.bank_account,
        )

    def test_empty_classification_is_allowed_for_later(self):
        form = BankStatementRowClassificationForm(
            data={
                "transaction_type": "",
                "category": "",
                "target_account": "",
                "payee": "",
                "skip_row": "",
            },
            instance=self.row,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_expense_with_category_is_valid(self):
        form = BankStatementRowClassificationForm(
            data={
                "transaction_type": "expense",
                "category": self.expense_category.pk,
                "target_account": "",
                "payee": "Vendor",
                "skip_row": "",
            },
            instance=self.row,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_type_without_category_is_allowed_as_incomplete(self):
        form = BankStatementRowClassificationForm(
            data={
                "transaction_type": "expense",
                "category": "",
                "target_account": "",
                "payee": "",
                "skip_row": "",
            },
            instance=self.row,
        )

        self.assertTrue(form.is_valid(), form.errors)
