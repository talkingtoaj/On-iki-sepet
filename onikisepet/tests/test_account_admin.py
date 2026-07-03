from django.contrib import admin
from django.test import TestCase

from onikisepet.models import Account

from .helpers import AccountTestMixin


class AccountAdminTests(AccountTestMixin, TestCase):
    def get_account_admin(self):
        return admin.site._registry[Account]

    def test_account_model_is_registered_in_admin(self):
        self.assertIn(Account, admin.site._registry)

    def test_account_admin_list_display_contains_expected_fields(self):
        account_admin = self.get_account_admin()

        self.assertEqual(
            list(account_admin.list_display),
            [
                "name",
                "account_type",
                "account_purpose",
                "currency",
                "opening_balance",
                "is_active",
                "created_at",
                "updated_at",
            ],
        )

    def test_account_admin_list_filter_contains_expected_fields(self):
        account_admin = self.get_account_admin()

        self.assertEqual(
            list(account_admin.list_filter),
            ["account_type", "account_purpose", "currency", "is_active"],
        )

    def test_account_admin_search_fields_contains_name(self):
        account_admin = self.get_account_admin()

        self.assertEqual(list(account_admin.search_fields), ["name"])
