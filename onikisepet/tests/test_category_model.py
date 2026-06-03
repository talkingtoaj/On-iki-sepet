from django.core.exceptions import ValidationError
from django.test import TestCase

from .helpers import CategoryTestMixin


class CategoryModelTests(CategoryTestMixin, TestCase):
    def test_category_can_be_created_with_income_type(self):
        category = self.create_category(name="Donation", category_type="income")
        type_field = self.get_category_type_field_name()

        self.assertEqual(category.name, "Donation")
        self.assertEqual(getattr(category, type_field), "income")

    def test_category_can_be_created_with_expense_type(self):
        category = self.create_category(name="Rent", category_type="expense")
        type_field = self.get_category_type_field_name()

        self.assertEqual(category.name, "Rent")
        self.assertEqual(getattr(category, type_field), "expense")

    def test_category_requires_a_name(self):
        category_model = self.get_category_model()
        category = category_model(
            **self.build_category_kwargs(name="", category_type="income")
        )

        with self.assertRaises(ValidationError):
            category.full_clean()

    def test_category_requires_a_valid_type(self):
        category_model = self.get_category_model()
        category = category_model(
            **self.build_category_kwargs(name="General", category_type="invalid")
        )

        with self.assertRaises(ValidationError):
            category.full_clean()

    def test_category_rejects_transfer_as_type(self):
        category_model = self.get_category_model()
        category = category_model(
            **self.build_category_kwargs(name="Transfer Bucket", category_type="transfer")
        )

        with self.assertRaises(ValidationError):
            category.full_clean()

    def test_category_name_must_be_unique(self):
        self.create_category(name="Bills", category_type="expense")
        duplicate = self.get_category_model()(
            **self.build_category_kwargs(name="Bills", category_type="expense")
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_str_returns_category_name(self):
        category = self.create_category(name="Hospitality", category_type="expense")

        self.assertEqual(str(category), "Hospitality")

    def test_inactive_categories_are_stored_but_marked_inactive(self):
        category = self.create_category(
            name="Legacy Expense",
            category_type="expense",
            is_active=False,
        )

        self.assertTrue(self.get_category_model().objects.filter(pk=category.pk).exists())
        self.assertFalse(category.is_active)
