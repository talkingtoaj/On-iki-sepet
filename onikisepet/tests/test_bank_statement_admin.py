from django.contrib import admin
from django.test import TestCase

from onikisepet.models import BankStatementImport, BankStatementRow


class BankStatementAdminTests(TestCase):
    def get_import_admin(self):
        return admin.site._registry[BankStatementImport]

    def get_row_admin(self):
        return admin.site._registry[BankStatementRow]

    def test_bank_statement_import_is_registered_in_admin(self):
        self.assertIn(BankStatementImport, admin.site._registry)

    def test_bank_statement_row_is_registered_in_admin(self):
        self.assertIn(BankStatementRow, admin.site._registry)

    def test_bank_statement_import_admin_list_display(self):
        import_admin = self.get_import_admin()

        expected_fields = [
            "original_filename",
            "status",
            "uploaded_by",
            "uploaded_at",
        ]

        self.assertEqual(list(import_admin.list_display), expected_fields)

    def test_bank_statement_row_admin_list_display(self):
        row_admin = self.get_row_admin()

        expected_fields = [
            "bank_statement_import",
            "row_number",
            "date",
            "amount",
            "currency",
            "account",
            "transaction_type",
            "is_skipped",
            "parse_error",
        ]

        self.assertEqual(list(row_admin.list_display), expected_fields)
