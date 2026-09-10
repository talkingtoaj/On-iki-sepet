import tempfile
from decimal import Decimal

from django.contrib import admin
from django.test import TestCase, override_settings

from onikisepet.models import Receipt

from .helpers import ReceiptFileTestMixin, TransactionTestMixin


class ReceiptAdminTests(TestCase):
    def get_receipt_admin(self):
        return admin.site._registry[Receipt]

    def test_receipt_model_is_registered_in_admin(self):
        self.assertIn(Receipt, admin.site._registry)

    def test_receipt_admin_list_display_contains_expected_fields(self):
        receipt_admin = self.get_receipt_admin()

        expected_fields = [
            "transaction",
            "original_filename",
            "file_link",
            "uploaded_by",
            "uploaded_at",
        ]

        self.assertEqual(list(receipt_admin.list_display), expected_fields)

    def test_receipt_admin_list_filter_contains_expected_fields(self):
        receipt_admin = self.get_receipt_admin()

        expected_filters = [
            "uploaded_at",
            "uploaded_by",
        ]

        self.assertEqual(list(receipt_admin.list_filter), expected_filters)

    def test_receipt_admin_search_fields_contains_expected_fields(self):
        receipt_admin = self.get_receipt_admin()

        expected_search_fields = [
            "original_filename",
            "transaction__payee",
            "transaction__description",
            "uploaded_by__username",
        ]

        self.assertEqual(list(receipt_admin.search_fields), expected_search_fields)

    def test_receipt_admin_readonly_fields_contains_uploaded_at(self):
        receipt_admin = self.get_receipt_admin()

        expected_readonly_fields = ["uploaded_at"]

        self.assertEqual(list(receipt_admin.readonly_fields), expected_readonly_fields)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ReceiptAdminFileLinkTests(
    ReceiptFileTestMixin, TransactionTestMixin, TestCase
):
    def get_receipt_admin(self):
        return admin.site._registry[Receipt]

    """Before this the admin listed a filename but gave no way to open the
    file, so an uploaded receipt could not actually be reviewed.
    """

    def setUp(self):
        self.user = self.create_user("receipt_link_user", is_superuser=True)
        self.cash_account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.expense_category = self.create_category(
            name="Supplies",
            category_type="expense",
        )
        self.transaction = self.create_transaction(
            transaction_type="expense",
            amount=Decimal("50.00"),
            source_account=self.cash_account,
            category=self.expense_category,
            created_by=self.user,
        )

    def _receipt(self):
        from onikisepet.models import Receipt

        uploaded = self.make_receipt_file("receipt.jpg")
        return Receipt.objects.create(
            transaction=self.transaction,
            file=uploaded,
            original_filename=uploaded.name,
            uploaded_by=self.user,
        )

    def test_file_link_points_at_the_stored_file(self):
        receipt = self._receipt()

        link = self.get_receipt_admin().file_link(receipt)

        self.assertIn(receipt.file.url, link)
        self.assertIn("<a", link)

    def test_file_link_handles_a_missing_file(self):
        from onikisepet.models import Receipt

        receipt = Receipt(
            transaction=self.transaction,
            original_filename="gone.jpg",
            uploaded_by=self.user,
        )

        self.assertEqual(self.get_receipt_admin().file_link(receipt), "-")
