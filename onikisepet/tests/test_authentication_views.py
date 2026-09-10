from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse

from onikisepet.usecases.roles import VIEWER

from .helpers import TransactionTestMixin


class LoginPageTests(TransactionTestMixin, TestCase):
    """Before this, LOGIN_URL pointed at /accounts/login/, which collided with
    the bank-account list and returned 404. Users who were not superusers had
    no way into the app at all.
    """

    def setUp(self):
        self.user = self.create_user("login_user")
        self.login_url = resolve_url(settings.LOGIN_URL)

    def test_login_page_exists_and_renders(self):
        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in")

    def test_login_url_does_not_collide_with_the_bank_account_list(self):
        self.assertNotEqual(self.login_url, reverse("account_list"))

    def test_redirect_from_a_protected_page_lands_on_a_working_login_page(self):
        protected_url = reverse("report_dashboard")

        response = self.client.get(protected_url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in")

    def test_valid_credentials_log_the_user_in(self):
        response = self.client.post(
            self.login_url,
            {"username": self.user.username, "password": self.password},
        )

        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_REDIRECT_URL),
            fetch_redirect_response=False,
        )

    def test_login_honours_the_next_parameter(self):
        target = reverse("transaction_list")

        response = self.client.post(
            f"{self.login_url}?next={target}",
            {"username": self.user.username, "password": self.password},
        )

        self.assertRedirects(response, target, fetch_redirect_response=False)

    def test_invalid_credentials_are_rejected(self):
        response = self.client.post(
            self.login_url,
            {"username": self.user.username, "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in")

    def test_user_can_log_out(self):
        self.client.login(username=self.user.username, password=self.password)

        response = self.client.post(reverse("logout"))

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)


class HomePageTests(TransactionTestMixin, TestCase):
    """The site root used to 404."""

    def setUp(self):
        self.user = self.create_user("home_user", group_name=VIEWER)

    def test_root_url_is_routed(self):
        self.client.login(username=self.user.username, password=self.password)

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)

    def test_root_url_redirects_anonymous_users_to_login(self):
        response = self.client.get("/", follow=True)

        self.assertContains(response, "Sign in")


class NavigationTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("nav_user", is_superuser=True)
        self.client.login(username=self.user.username, password=self.password)

    def test_pages_share_navigation_between_sections(self):
        response = self.client.get(reverse("report_dashboard"))

        for url_name in [
            "report_dashboard",
            "transaction_list",
            "account_list",
            "category_list",
            "exchange_rate_list",
        ]:
            self.assertContains(response, reverse(url_name))

    def test_navigation_shows_the_signed_in_user(self):
        response = self.client.get(reverse("report_dashboard"))

        self.assertContains(response, self.user.username)

    def test_navigation_offers_a_logout_control(self):
        response = self.client.get(reverse("report_dashboard"))

        self.assertContains(response, reverse("logout"))
