from decimal import Decimal

from django.test import TestCase

from onikisepet.models import Receipt, Transaction

from .helpers import TransactionTestMixin


class ReceiptDataModelDesignTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("receipt_design_user")
        self.cash_account = self.create_account(
            name="Receipt Design Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.expense_category = self.create_category(
            name="Receipt Design Expense",
            category_type="expense",
        )

    def test_transaction_does_not_have_receipt_filename_field(self):
        field_names = {field.name for field in Transaction._meta.fields}

        self.assertNotIn("receipt_filename", field_names)
        self.assertNotIn("receipt_file", field_names)

    def test_receipt_stores_original_filename_linked_to_transaction(self):
        transaction = self.create_transaction(
            transaction_type="expense",
            amount=Decimal("50.00"),
            source_account=self.cash_account,
            category=self.expense_category,
            created_by=self.user,
        )
        receipt = Receipt.objects.create(
            transaction=transaction,
            file="receipts/test.jpg",
            original_filename="market-fisi.jpg",
            uploaded_by=self.user,
        )

        self.assertEqual(transaction.receipts.get(), receipt)
        self.assertEqual(receipt.original_filename, "market-fisi.jpg")
