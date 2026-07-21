from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from onikisepet.kut_categories import KUT_CATEGORIES, load_kut_categories
from onikisepet.models import Category


class KutCategoriesTests(TestCase):
    def test_kut_categories_spec_defines_income_and_expense_categories(self):
        income_count = sum(
            1
            for spec in KUT_CATEGORIES
            if spec["category_type"] == Category.CategoryType.INCOME
        )
        expense_count = sum(
            1
            for spec in KUT_CATEGORIES
            if spec["category_type"] == Category.CategoryType.EXPENSE
        )

        self.assertGreater(income_count, 0)
        self.assertGreater(expense_count, 0)
        self.assertEqual(len(KUT_CATEGORIES), income_count + expense_count)

    def test_seed_migration_loads_kut_categories_in_test_database(self):
        self.assertEqual(Category.objects.count(), len(KUT_CATEGORIES))

    def test_load_kut_categories_is_idempotent_after_seed(self):
        created_count = load_kut_categories()

        self.assertEqual(created_count, 0)
        self.assertEqual(Category.objects.count(), len(KUT_CATEGORIES))

    def test_load_kut_categories_sets_expected_fields(self):
        for spec in KUT_CATEGORIES:
            with self.subTest(name=spec["name"]):
                category = Category.objects.get(name=spec["name"])
                self.assertEqual(category.category_type, spec["category_type"])
                self.assertTrue(category.is_active)

    def test_load_kut_categories_creates_expected_income_categories(self):
        self.assertTrue(
            Category.objects.filter(
                name="Bağış",
                category_type=Category.CategoryType.INCOME,
            ).exists()
        )
        self.assertTrue(
            Category.objects.filter(
                name="Online Bağış",
                category_type=Category.CategoryType.INCOME,
            ).exists()
        )

    def test_load_kut_categories_creates_expected_expense_categories(self):
        self.assertTrue(
            Category.objects.filter(
                name="Kira",
                category_type=Category.CategoryType.EXPENSE,
            ).exists()
        )
        self.assertTrue(
            Category.objects.filter(
                name="Faturalar",
                category_type=Category.CategoryType.EXPENSE,
            ).exists()
        )

    def test_load_kut_categories_does_not_overwrite_existing_category_fields(self):
        Category.objects.all().delete()
        Category.objects.create(
            name="Bağış",
            category_type=Category.CategoryType.EXPENSE,
            is_active=False,
        )

        created_count = load_kut_categories()

        category = Category.objects.get(name="Bağış")
        self.assertEqual(created_count, len(KUT_CATEGORIES) - 1)
        self.assertEqual(category.category_type, Category.CategoryType.EXPENSE)
        self.assertFalse(category.is_active)


class LoadKutCategoriesCommandTests(TestCase):
    def test_command_reports_seed_categories_when_already_loaded(self):
        self.assertEqual(Category.objects.count(), len(KUT_CATEGORIES))
        stdout = StringIO()

        call_command("load_kut_categories", stdout=stdout)

        self.assertIn(
            f"Zaten mevcut kategori sayısı: {len(KUT_CATEGORIES)}",
            stdout.getvalue(),
        )

    def test_command_reports_existing_categories_on_second_run(self):
        load_kut_categories()
        stdout = StringIO()

        call_command("load_kut_categories", stdout=stdout)

        self.assertIn(
            f"Zaten mevcut kategori sayısı: {len(KUT_CATEGORIES)}",
            stdout.getvalue(),
        )
        self.assertNotIn("Oluşturulan kategori sayısı:", stdout.getvalue())
