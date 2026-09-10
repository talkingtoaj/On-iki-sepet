# These tests assert the English wording of the interface. The app now
# defaults to Turkish, so the language is pinned here rather than left
# implicit; Turkish rendering is covered in test_localization.py.
from decimal import Decimal

from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase, override_settings
from django.urls import reverse

from .helpers import ExchangeRateTestMixin, TransactionTestMixin


@override_settings(LANGUAGE_CODE="en")
class ExchangeRateViewTests(ExchangeRateTestMixin, TransactionTestMixin, TestCase):
    def setUp(self):
        self.list_url = reverse("exchange_rate_list")
        self.create_url = reverse("exchange_rate_create")
        self.admin_user = self.create_user("fx_admin", is_superuser=True)
        self.data_entry_user = self.create_user("fx_entry", group_name="Data Entry")

    def _valid_payload(self):
        return {
            "currency": "USD",
            "rate_to_base": "34.00",
            "effective_date": "2026-09-01",
        }

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.list_url)

        login_url = resolve_url(settings.LOGIN_URL)
        self.assertRedirects(
            response,
            f"{login_url}?next={self.list_url}",
            fetch_redirect_response=False,
        )

    def test_logged_in_user_can_view_the_rate_list(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)

    def test_rate_list_shows_existing_rates(self):
        self.create_exchange_rate(
            currency="USD",
            rate_to_base=Decimal("34.00"),
            effective_date="2026-09-01",
        )
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.list_url)

        self.assertContains(response, "USD")
        self.assertContains(response, "34.00")

    def test_rate_list_shows_empty_state(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.list_url)

        self.assertContains(response, "No exchange rates")

    def test_admin_can_create_a_rate(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(self.create_url, self._valid_payload())

        self.assertRedirects(response, self.list_url)
        self.assertEqual(self.get_exchange_rate_model().objects.count(), 1)

    def test_data_entry_user_cannot_create_a_rate(self):
        """Rates change every reported figure, so they are a treasurer job."""
        self.client.login(
            username=self.data_entry_user.username, password=self.password
        )

        response = self.client.post(self.create_url, self._valid_payload())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.get_exchange_rate_model().objects.count(), 0)

    def test_invalid_rate_is_redisplayed_with_errors(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            self.create_url, {**self._valid_payload(), "rate_to_base": "0"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_exchange_rate_model().objects.count(), 0)
