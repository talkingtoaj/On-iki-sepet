from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from onikisepet.forms import BankStatementUploadForm


class BankStatementUploadFormTests(TestCase):
    def test_valid_csv_file_is_accepted(self):
        uploaded_file = SimpleUploadedFile(
            "statement.csv",
            b"date,description,amount,currency,account\n",
            content_type="text/csv",
        )
        form = BankStatementUploadForm({}, {"file": uploaded_file})

        self.assertTrue(form.is_valid())

    def test_invalid_extension_is_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "statement.txt",
            b"date,description,amount,currency,account\n",
            content_type="text/plain",
        )
        form = BankStatementUploadForm({}, {"file": uploaded_file})

        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)

    def test_xlsx_extension_is_accepted(self):
        uploaded_file = SimpleUploadedFile(
            "statement.xlsx",
            b"placeholder",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        form = BankStatementUploadForm({}, {"file": uploaded_file})

        self.assertTrue(form.is_valid())

    def test_pdf_extension_requires_default_account(self):
        uploaded_file = SimpleUploadedFile(
            "statement.pdf",
            b"%PDF-1.4",
            content_type="application/pdf",
        )
        form = BankStatementUploadForm({}, {"file": uploaded_file})

        self.assertFalse(form.is_valid())
        self.assertIn("default_account", form.errors)
