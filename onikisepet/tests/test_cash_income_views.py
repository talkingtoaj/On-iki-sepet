from decimal import Decimal

from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse

from onikisepet.models import Receipt

from .helpers import TransactionTestMixin


class CashIncomeViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.cash_income_create_url = reverse("cash_income_create")
        self.transaction_list_url = reverse("transaction_list")

        self.admin_user = self.create_user("cash_income_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "cash_income_data_entry",
            group_name="Data Entry",
        )
        self.viewer_user = self.create_user(
            "cash_income_viewer",
            group_name="Viewer",
        )

        self.cash_account = self.create_account(
            name="Kasa",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Elden Bağış",
            category_type="income",
        )

    def _valid_payload(self):
        return {
            "date": "2026-06-13",
            "donor_name": "Ayşe Demir",
            "amount": "200.00",
            "cash_account": self.cash_account.pk,
            "category": self.income_category.pk,
            "description": "Elden bağış",
        }

    def test_admin_can_access_cash_income_create_page(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.cash_income_create_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Defter")

    def test_data_entry_can_access_cash_income_create_page(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.cash_income_create_url)

        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_access_cash_income_create_page(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.cash_income_create_url)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.cash_income_create_url)

        login_url = resolve_url(settings.LOGIN_URL)
        expected_redirect = f"{login_url}?next={self.cash_income_create_url}"
        self.assertRedirects(
            response,
            expected_redirect,
            fetch_redirect_response=False,
        )

    def test_admin_can_create_cash_income(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(self.cash_income_create_url, data=self._valid_payload())

        self.assertRedirects(response, self.transaction_list_url)
        transaction = self.get_transaction_model().objects.get()
        self.assertEqual(transaction.transaction_type, "income")
        self.assertEqual(transaction.payee, "Ayşe Demir")
        self.assertEqual(transaction.amount, Decimal("200.00"))
        self.assertEqual(transaction.target_account, self.cash_account)

    def test_cash_income_create_does_not_create_receipt(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(self.cash_income_create_url, data=self._valid_payload())

        self.assertEqual(Receipt.objects.count(), 0)

    def test_successful_cash_income_create_redirects_to_transaction_list(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(self.cash_income_create_url, data=self._valid_payload())

        self.assertRedirects(response, self.transaction_list_url)
