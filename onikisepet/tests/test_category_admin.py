from django.contrib import admin
from django.test import TestCase

from onikisepet.models import Category

from .helpers import CategoryTestMixin


class CategoryAdminTests(CategoryTestMixin, TestCase):
    def get_category_admin(self):
        return admin.site._registry[Category]

    def test_category_model_is_registered_in_admin(self):
        self.assertIn(Category, admin.site._registry)

    def test_category_admin_list_display_contains_expected_fields(self):
        category_admin = self.get_category_admin()

        self.assertEqual(
            list(category_admin.list_display),
            ["name", "category_type", "is_active", "created_at", "updated_at"],
        )

    def test_category_admin_list_filter_contains_expected_fields(self):
        category_admin = self.get_category_admin()

        self.assertEqual(
            list(category_admin.list_filter),
            ["category_type", "is_active"],
        )

    def test_category_admin_search_fields_contains_name(self):
        category_admin = self.get_category_admin()

        self.assertEqual(list(category_admin.search_fields), ["name"])
