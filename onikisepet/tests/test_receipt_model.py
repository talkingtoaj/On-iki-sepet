from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .helpers import TransactionTestMixin


class ReceiptModelTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("receipt_user")
        self.cash_account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.bank_account = self.create_account(
            name="Bank Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.expense_category = self.create_category(
            name="Cash Expense",
            category_type="expense",
        )
        self.income_category = self.create_category(
            name="Donation",
            category_type="income",
        )

    def get_receipt_model(self):
        try:
            from onikisepet.models import Receipt
        except ImportError as exc:
            raise AssertionError("Receipt model must be implemented.") from exc

        return Receipt

    def create_uploaded_file(self, name="receipt.jpg"):
        return SimpleUploadedFile(
            name,
            b"fake receipt content",
            content_type="image/jpeg",
        )

    def create_cash_expense_transaction(self):
        return self.create_transaction(
            transaction_type="expense",
            amount=Decimal("125.00"),
            source_account=self.cash_account,
            category=self.expense_category,
            description="Cash grocery reimbursement",
            created_by=self.user,
        )

    def create_bank_expense_transaction(self):
        return self.create_transaction(
            transaction_type="expense",
            amount=Decimal("250.00"),
            source_account=self.bank_account,
            category=self.expense_category,
            created_by=self.user,
        )

    def create_income_transaction(self):
        return self.create_transaction(
            transaction_type="income",
            amount=Decimal("500.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.user,
        )

    def create_transfer_transaction(self):
        return self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("100.00"),
            source_account=self.cash_account,
            target_account=self.bank_account,
            created_by=self.user,
        )

    def test_receipt_model_exists(self):
        receipt_model = self.get_receipt_model()

        self.assertEqual(receipt_model.__name__, "Receipt")

    def test_receipt_can_be_created_for_cash_expense_transaction(self):
        receipt_model = self.get_receipt_model()
        transaction = self.create_cash_expense_transaction()

        receipt = receipt_model.objects.create(
            transaction=transaction,
            file=self.create_uploaded_file(),
            original_filename="receipt.jpg",
            uploaded_by=self.user,
        )

        self.assertEqual(receipt.transaction, transaction)

    def test_receipt_requires_transaction(self):
        receipt_model = self.get_receipt_model()
        receipt = receipt_model(
            file=self.create_uploaded_file(),
            original_filename="receipt.jpg",
            uploaded_by=self.user,
        )

        with self.assertRaises(ValidationError):
            receipt.full_clean()

    def test_receipt_requires_file(self):
        receipt_model = self.get_receipt_model()
        receipt = receipt_model(
            transaction=self.create_cash_expense_transaction(),
            original_filename="receipt.jpg",
            uploaded_by=self.user,
        )

        with self.assertRaises(ValidationError):
            receipt.full_clean()

    def test_receipt_stores_original_filename(self):
        receipt_model = self.get_receipt_model()

        receipt = receipt_model.objects.create(
            transaction=self.create_cash_expense_transaction(),
            file=self.create_uploaded_file("migros.jpg"),
            original_filename="migros.jpg",
            uploaded_by=self.user,
        )

        self.assertEqual(receipt.original_filename, "migros.jpg")

    def test_receipt_stores_uploaded_by(self):
        receipt_model = self.get_receipt_model()

        receipt = receipt_model.objects.create(
            transaction=self.create_cash_expense_transaction(),
            file=self.create_uploaded_file(),
            original_filename="receipt.jpg",
            uploaded_by=self.user,
        )

        self.assertEqual(receipt.uploaded_by, self.user)

    def test_receipt_uploaded_at_is_set_automatically(self):
        receipt_model = self.get_receipt_model()

        receipt = receipt_model.objects.create(
            transaction=self.create_cash_expense_transaction(),
            file=self.create_uploaded_file(),
            original_filename="receipt.jpg",
            uploaded_by=self.user,
        )

        self.assertIsNotNone(receipt.uploaded_at)

    def test_receipt_rejects_income_transaction(self):
        receipt_model = self.get_receipt_model()
        receipt = receipt_model(
            transaction=self.create_income_transaction(),
            file=self.create_uploaded_file(),
            original_filename="receipt.jpg",
            uploaded_by=self.user,
        )

        with self.assertRaises(ValidationError):
            receipt.full_clean()

    def test_receipt_rejects_transfer_transaction(self):
        receipt_model = self.get_receipt_model()
        receipt = receipt_model(
            transaction=self.create_transfer_transaction(),
            file=self.create_uploaded_file(),
            original_filename="receipt.jpg",
            uploaded_by=self.user,
        )

        with self.assertRaises(ValidationError):
            receipt.full_clean()

    def test_receipt_rejects_bank_expense_transaction(self):
        receipt_model = self.get_receipt_model()
        receipt = receipt_model(
            transaction=self.create_bank_expense_transaction(),
            file=self.create_uploaded_file(),
            original_filename="receipt.jpg",
            uploaded_by=self.user,
        )

        with self.assertRaises(ValidationError):
            receipt.full_clean()

    def test_receipt_str_returns_readable_value(self):
        receipt_model = self.get_receipt_model()

        receipt = receipt_model.objects.create(
            transaction=self.create_cash_expense_transaction(),
            file=self.create_uploaded_file("migros.jpg"),
            original_filename="migros.jpg",
            uploaded_by=self.user,
        )

        value = str(receipt)

        self.assertIn("migros.jpg", value)
