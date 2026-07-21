from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse

from .helpers import CategoryTestMixin, SEED_CATEGORY_COUNT


class CategoryViewTests(CategoryTestMixin, TestCase):
    password = "StrongTestPass123!"

    def setUp(self):
        self.category_list_url = reverse("category_list")
        self.category_create_url = reverse("category_create")

        self.admin_user = self._create_admin_user("admin_user")
        self.data_entry_user = self._create_group_user("data_entry_user", "Data Entry")
        self.viewer_user = self._create_group_user("viewer_user", "Viewer")

    def _create_admin_user(self, username):
        user_model = get_user_model()
        return user_model.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password=self.password,
            is_staff=True,
            is_superuser=True,
        )

    def _create_group_user(self, username, group_name):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password=self.password,
        )
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
        return user

    def test_logged_in_admin_can_access_category_list_page(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.category_list_url)

        self.assertEqual(response.status_code, 200)

    def test_logged_in_data_entry_user_can_access_category_list_page(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.category_list_url)

        self.assertEqual(response.status_code, 200)

    def test_logged_in_viewer_user_cannot_access_category_list_page(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.category_list_url)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_login_from_category_list_page(self):
        response = self.client.get(self.category_list_url)

        login_url = resolve_url(settings.LOGIN_URL)
        expected_redirect = f"{login_url}?next={self.category_list_url}"
        self.assertRedirects(
            response,
            expected_redirect,
            fetch_redirect_response=False,
        )

    def test_admin_can_access_category_create_page(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.category_create_url)

        self.assertEqual(response.status_code, 200)

    def test_data_entry_user_cannot_access_category_create_page(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.category_create_url)

        self.assertEqual(response.status_code, 403)

    def test_viewer_user_cannot_access_category_create_page(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.category_create_url)

        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_income_category_with_post(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self.build_category_kwargs(name="Donation", category_type="income")

        response = self.client.post(self.category_create_url, data=payload)

        self.assertEqual(
            self.get_category_model().objects.count(),
            SEED_CATEGORY_COUNT + 1,
        )
        self.assertRedirects(response, self.category_list_url)

    def test_admin_can_create_expense_category_with_post(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self.build_category_kwargs(name="Rent", category_type="expense")

        response = self.client.post(self.category_create_url, data=payload)

        self.assertEqual(
            self.get_category_model().objects.count(),
            SEED_CATEGORY_COUNT + 1,
        )
        self.assertRedirects(response, self.category_list_url)

    def test_after_successful_creation_user_is_redirected_to_category_list(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self.build_category_kwargs(name="Bills", category_type="expense")

        response = self.client.post(self.category_create_url, data=payload)

        self.assertRedirects(response, self.category_list_url)

    def test_category_list_displays_existing_categories(self):
        self.create_category(name="Donation", category_type="income")
        self.create_category(name="Hospitality", category_type="expense")
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.category_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Donation")
        self.assertContains(response, "Hospitality")

    def test_category_list_displays_empty_message_when_there_are_no_categories(self):
        self.get_category_model().objects.all().delete()
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.category_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Henüz kategori bulunamadı.")