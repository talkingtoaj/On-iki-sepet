from decimal import Decimal

from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse

from .helpers import ProfileTestMixin, TransactionTestMixin


class TransactionViewTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def setUp(self):
        self.transaction_list_url = reverse("transaction_list")

        self.admin_user = self.create_user("transaction_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "transaction_data_entry",
            group_name="Data Entry",
        )
        self.approver_user = self.create_data_entry_approver("transaction_approver")
        self.viewer_user = self.create_user("transaction_viewer", group_name="Viewer")

        self.cash_account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Donation",
            category_type="income",
        )

    def test_logged_in_admin_can_access_transaction_list_page(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.transaction_list_url)

        self.assertEqual(response.status_code, 200)

    def test_logged_in_data_entry_user_can_access_transaction_list_page(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.transaction_list_url)

        self.assertEqual(response.status_code, 200)

    def test_logged_in_approver_user_can_access_transaction_list_page(self):
        self.client.login(username=self.approver_user.username, password=self.password)

        response = self.client.get(self.transaction_list_url)

        self.assertEqual(response.status_code, 200)

    def test_logged_in_viewer_user_cannot_access_transaction_list_page(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.transaction_list_url)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_login_from_transaction_list_page(self):
        response = self.client.get(self.transaction_list_url)

        login_url = resolve_url(settings.LOGIN_URL)
        expected_redirect = f"{login_url}?next={self.transaction_list_url}"
        self.assertRedirects(
            response,
            expected_redirect,
            fetch_redirect_response=False,
        )

    def test_transaction_list_displays_existing_transactions(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=self.cash_account,
            category=self.income_category,
            description="Sunday donation",
            created_by=self.admin_user,
        )
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.transaction_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sunday donation")

    def test_transaction_list_displays_empty_message_when_there_are_no_transactions(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.transaction_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Henüz işlem bulunamadı.")
