from django.core.management import call_command
from django.test import TestCase

from onikisepet.kut_categories import KUT_CATEGORIES
from onikisepet.models import Category

from .helpers import CategoryTestMixin


class LoadKutCategoriesCommandTests(CategoryTestMixin, TestCase):
    def test_load_kut_categories_creates_default_categories(self):
        call_command("load_kut_categories")

        self.assertEqual(Category.objects.count(), len(KUT_CATEGORIES))
        self.assertTrue(
            Category.objects.filter(
                name="Bağış",
                category_type=Category.CategoryType.INCOME,
            ).exists()
        )
        self.assertTrue(
            Category.objects.filter(
                name="Kira",
                category_type=Category.CategoryType.EXPENSE,
            ).exists()
        )

    def test_load_kut_categories_is_idempotent(self):
        call_command("load_kut_categories")
        call_command("load_kut_categories")

        self.assertEqual(Category.objects.count(), len(KUT_CATEGORIES))
