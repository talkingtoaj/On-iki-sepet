from django.test import TestCase
from django.urls import reverse

from .helpers import TransactionTestMixin


class AuthViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.login_url = reverse("login")
        self.logout_url = reverse("logout")
        self.home_url = reverse("home")
        self.user = self.create_user("auth_user")

    def test_login_page_is_accessible_for_anonymous_users(self):
        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "KUT Finans")
        self.assertContains(response, "Giriş yap")

    def test_successful_login_redirects_to_home(self):
        response = self.client.post(
            self.login_url,
            data={
                "username": self.user.username,
                "password": self.password,
            },
        )

        self.assertRedirects(response, self.home_url, fetch_redirect_response=False)

    def test_successful_login_honors_next_parameter(self):
        transaction_list_url = reverse("transaction_list")
        login_with_next = f"{self.login_url}?next={transaction_list_url}"

        response = self.client.post(
            login_with_next,
            data={
                "username": self.user.username,
                "password": self.password,
            },
        )

        self.assertRedirects(
            response,
            transaction_list_url,
            fetch_redirect_response=False,
        )

    def test_logout_redirects_to_login_page(self):
        self.client.login(username=self.user.username, password=self.password)

        response = self.client.post(self.logout_url)

        self.assertRedirects(response, self.login_url, fetch_redirect_response=False)

        home_response = self.client.get(self.home_url)
        login_redirect = f"{self.login_url}?next={self.home_url}"
        self.assertRedirects(
            home_response,
            login_redirect,
            fetch_redirect_response=False,
        )
