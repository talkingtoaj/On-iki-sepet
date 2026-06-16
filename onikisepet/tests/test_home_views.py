from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse

from .helpers import TransactionTestMixin


class HomeViewAccessTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.home_url = reverse("home")
        self.admin_user = self.create_user("home_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "home_data_entry",
            group_name="Data Entry",
        )
        self.viewer_user = self.create_user("home_viewer", group_name="Viewer")

    def _login(self, user):
        self.client.login(username=user.username, password=self.password)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.home_url)

        login_url = resolve_url(settings.LOGIN_URL)
        self.assertRedirects(
            response,
            f"{login_url}?next={self.home_url}",
            fetch_redirect_response=False,
        )

    def test_admin_can_access_home(self):
        self._login(self.admin_user)

        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)

    def test_data_entry_user_can_access_home(self):
        self._login(self.data_entry_user)

        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)

    def test_viewer_can_access_home(self):
        self._login(self.viewer_user)

        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)


class NavigationMenuTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.home_url = reverse("home")
        self.admin_user = self.create_user("nav_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "nav_data_entry",
            group_name="Data Entry",
        )
        self.viewer_user = self.create_user("nav_viewer", group_name="Viewer")

        self.main_menu_links = {
            "Raporlar": reverse("report_dashboard"),
            "İşlemler": reverse("transaction_list"),
            "Hesaplar": reverse("account_list"),
            "Kategoriler": reverse("category_list"),
        }
        self.transaction_create_menu_links = {
            "Nakit Gelir": reverse("cash_income_create"),
            "Nakit Gider": reverse("cash_expense_create"),
            "Banka Gideri": reverse("bank_expense_create"),
            "Online Bağış": reverse("online_donation_income_create"),
            "Transfer": reverse("transfer_create"),
        }
        self.setup_create_links = {
            "Kategori Oluştur": reverse("category_create"),
            "Hesap Oluştur": reverse("account_create"),
        }
        self.transaction_create_link = {
            "İşlem Oluştur": reverse("transaction_create"),
        }

    def _login(self, user):
        self.client.login(username=user.username, password=self.password)

    def _assert_contains_links(self, response, links):
        for label, url in links.items():
            with self.subTest(label=label):
                self.assertContains(response, label)
                self.assertContains(response, f'href="{url}"')

    def _assert_not_contains_links(self, response, links):
        for label, url in links.items():
            with self.subTest(label=label):
                self.assertNotContains(response, f'href="{url}"')

    def test_authenticated_users_see_main_menu_links(self):
        for user in (self.admin_user, self.data_entry_user, self.viewer_user):
            with self.subTest(user=user.username):
                self._login(user)
                response = self.client.get(self.home_url)
                self._assert_contains_links(response, self.main_menu_links)

    def test_admin_sees_all_create_links(self):
        self._login(self.admin_user)

        response = self.client.get(self.home_url)

        self._assert_contains_links(response, self.transaction_create_menu_links)
        self._assert_contains_links(response, self.setup_create_links)
        self._assert_contains_links(response, self.transaction_create_link)

    def test_data_entry_sees_transaction_create_links_only(self):
        self._login(self.data_entry_user)

        response = self.client.get(self.home_url)

        self._assert_contains_links(response, self.transaction_create_menu_links)
        self._assert_contains_links(response, self.transaction_create_link)
        self._assert_not_contains_links(response, self.setup_create_links)

    def test_viewer_does_not_see_create_links(self):
        self._login(self.viewer_user)

        response = self.client.get(self.home_url)

        self._assert_not_contains_links(response, self.transaction_create_menu_links)
        self._assert_not_contains_links(response, self.setup_create_links)
        self._assert_not_contains_links(response, self.transaction_create_link)
