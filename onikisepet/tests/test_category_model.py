from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from .helpers import CategoryTestMixin


@override_settings(LANGUAGE_CODE="en")
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

    def test_category_name_must_be_unique_within_a_type(self):
        self.create_category(name="Bills", category_type="expense")
        duplicate = self.get_category_model()(
            **self.build_category_kwargs(name="Bills", category_type="expense")
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_the_same_name_is_allowed_for_income_and_expense(self):
        """A church commonly needs a "Missions" income category for gifts
        received and a "Missions" expense category for gifts sent. A globally
        unique name made that impossible.
        """
        self.create_category(name="Missions", category_type="income")
        expense_twin = self.get_category_model()(
            **self.build_category_kwargs(
                name="Missions", category_type="expense"
            )
        )

        expense_twin.full_clean()
        expense_twin.save()

        self.assertEqual(
            self.get_category_model().objects.filter(name="Missions").count(), 2
        )

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
