from typing import Any

from django.test import TestCase

from .helpers import CategoryTestMixin


class CategoryFormTests(CategoryTestMixin, TestCase):
    def _build_form_data(
        self,
        *,
        name="Donation",
        category_type="income",
        is_active=True,
    ) -> dict[str, Any]:
        category_form_class = self.get_category_form_class()
        field_names = set(category_form_class().fields.keys())
        type_field = self._resolve_type_field_name(field_names)

        data: dict[str, Any] = {
            "name": name,
            type_field: category_type,
        }
        if "is_active" in field_names:
            data["is_active"] = is_active
        return data

    def test_form_is_valid_with_name_and_valid_type(self):
        category_form_class = self.get_category_form_class()
        form = category_form_class(
            data=self._build_form_data(name="Donation", category_type="income")
        )

        self.assertTrue(form.is_valid())

    def test_form_is_invalid_without_name(self):
        category_form_class = self.get_category_form_class()
        form = category_form_class(
            data=self._build_form_data(name="", category_type="income")
        )

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_form_is_invalid_without_type(self):
        category_form_class = self.get_category_form_class()
        data = self._build_form_data(name="Rent", category_type="expense")
        type_field = self._resolve_type_field_name(set(category_form_class().fields.keys()))
        data.pop(type_field)
        form = category_form_class(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn(type_field, form.errors)

    def test_form_is_invalid_with_invalid_type(self):
        category_form_class = self.get_category_form_class()
        form = category_form_class(
            data=self._build_form_data(name="Unknown", category_type="invalid")
        )

        self.assertFalse(form.is_valid())
        type_field = self._resolve_type_field_name(set(category_form_class().fields.keys()))
        self.assertIn(type_field, form.errors)

    def test_form_is_invalid_with_duplicate_category_name(self):
        self.create_category(name="Bills", category_type="expense")
        category_form_class = self.get_category_form_class()
        form = category_form_class(
            data=self._build_form_data(name="Bills", category_type="expense")
        )

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
