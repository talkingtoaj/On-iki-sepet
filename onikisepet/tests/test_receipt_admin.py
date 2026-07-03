from django.contrib import admin
from django.test import TestCase

from onikisepet.models import Receipt


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
            "file_type",
            "uploaded_by",
            "uploaded_at",
        ]

        self.assertEqual(list(receipt_admin.list_display), expected_fields)

    def test_receipt_admin_list_filter_contains_expected_fields(self):
        receipt_admin = self.get_receipt_admin()

        expected_filters = [
            "file_type",
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
