from decimal import Decimal

from django.test import TestCase

from onikisepet.models import BankStatementImport, BankStatementRow

from .helpers import TransactionTestMixin


class BankStatementImportModelTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("import_model_user")
        self.bank_account = self.create_account(
            name="Main Expense Bank Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )

    def test_bank_statement_import_can_be_created(self):
        bank_import = BankStatementImport.objects.create(
            uploaded_by=self.user,
            original_filename="statement.csv",
        )

        self.assertEqual(bank_import.status, BankStatementImport.Status.PREVIEW)
        self.assertEqual(str(bank_import), "statement.csv")

    def test_bank_statement_row_stores_parsed_values(self):
        bank_import = BankStatementImport.objects.create(
            uploaded_by=self.user,
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

        self.assertTrue(row.is_parse_valid)
        self.assertIn("Internet bill", str(row))
