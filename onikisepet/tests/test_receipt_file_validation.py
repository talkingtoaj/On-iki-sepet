from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from onikisepet.constants import RECEIPT_FILE_ACCEPT
from onikisepet.forms import BankExpenseForm, CashExpenseForm
from onikisepet.models import Receipt

from .helpers import TransactionTestMixin


class ReceiptFileValidationTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.cash_expense_create_url = reverse("cash_expense_create")
        self.admin_user = self.create_user("receipt_validation_admin", is_superuser=True)
        self.cash_account = self.create_account(
            name="Receipt Validation Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.expense_category = self.create_category(
            name="Receipt Validation Expense",
            category_type="expense",
        )

    def _uploaded_file(self, name, content_type):
        return SimpleUploadedFile(
            name,
            b"dummy receipt content",
            content_type=content_type,
        )

    def _form_data(self):
        return {
            "date": "2026-06-13",
            "payee": "Migros",
            "amount": "125.50",
            "cash_account": str(self.cash_account.pk),
            "category": str(self.expense_category.pk),
            "description": "Cash expense with receipt",
        }

    def _form(self, uploaded_file):
        return CashExpenseForm(
            data=self._form_data(),
            files={"receipt_file": uploaded_file},
        )

    def _post_payload(self, uploaded_file):
        payload = self._form_data()
        payload["receipt_file"] = uploaded_file
        return payload

    def _transaction_model(self):
        return self.get_transaction_model()

    def test_cash_expense_form_accepts_pdf_receipt(self):
        form = self._form(
            self._uploaded_file("receipt.pdf", "application/pdf"),
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_cash_expense_form_accepts_jpg_receipt(self):
        form = self._form(
            self._uploaded_file("receipt.jpg", "image/jpeg"),
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_cash_expense_form_accepts_jpeg_receipt(self):
        form = self._form(
            self._uploaded_file("receipt.jpeg", "image/jpeg"),
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_cash_expense_form_accepts_png_receipt(self):
        form = self._form(
            self._uploaded_file("receipt.png", "image/png"),
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_cash_expense_form_rejects_txt_receipt(self):
        form = self._form(
            self._uploaded_file("notes.txt", "text/plain"),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("receipt_file", form.errors)

    def test_cash_expense_form_rejects_docx_receipt(self):
        form = self._form(
            self._uploaded_file(
                "receipt.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("receipt_file", form.errors)

    def test_cash_expense_form_rejects_zip_receipt(self):
        form = self._form(
            self._uploaded_file("archive.zip", "application/zip"),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("receipt_file", form.errors)

    def test_cash_expense_form_rejects_exe_receipt(self):
        form = self._form(
            self._uploaded_file("malware.exe", "application/octet-stream"),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("receipt_file", form.errors)

    def test_cash_expense_form_rejects_file_without_extension(self):
        form = self._form(
            self._uploaded_file("receipt", "application/octet-stream"),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("receipt_file", form.errors)

    def test_cash_expense_receipt_file_widget_accepts_images_and_pdf(self):
        form = CashExpenseForm()

        self.assertEqual(
            form.fields["receipt_file"].widget.attrs["accept"],
            RECEIPT_FILE_ACCEPT,
        )
        self.assertIn("Telefondan fotoğraf", form.fields["receipt_file"].help_text)

    def test_bank_expense_receipt_file_widget_accepts_images_and_pdf(self):
        form = BankExpenseForm()

        self.assertEqual(
            form.fields["receipt_file"].widget.attrs["accept"],
            RECEIPT_FILE_ACCEPT,
        )
        self.assertFalse(form.fields["receipt_file"].required)
        self.assertIn("Telefondan fotoğraf", form.fields["receipt_file"].help_text)

    def test_invalid_receipt_file_does_not_create_transaction(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            self.cash_expense_create_url,
            data=self._post_payload(
                self._uploaded_file("malware.exe", "application/octet-stream"),
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("receipt_file", response.context["form"].errors)
        self.assertEqual(self._transaction_model().objects.count(), 0)

    def test_invalid_receipt_file_does_not_create_receipt(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            self.cash_expense_create_url,
            data=self._post_payload(
                self._uploaded_file("malware.exe", "application/octet-stream"),
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("receipt_file", response.context["form"].errors)
        self.assertEqual(Receipt.objects.count(), 0)
