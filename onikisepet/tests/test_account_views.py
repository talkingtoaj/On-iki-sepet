from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse

from .helpers import AccountTestMixin, SEED_ACCOUNT_COUNT, TransactionTestMixin


class AccountViewTests(AccountTestMixin, TransactionTestMixin, TestCase):
    password = "StrongTestPass123!"

    def setUp(self):
        self.account_list_url = reverse("account_list")
        self.account_create_url = reverse("account_create")

        self.admin_user = self._create_admin_user("admin_account_user")
        self.data_entry_user = self._create_group_user(
            "data_entry_account_user",
            "Data Entry",
        )
        self.viewer_user = self._create_group_user("viewer_account_user", "Viewer")

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

    def test_logged_in_admin_can_access_account_list_page(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.account_list_url)

        self.assertEqual(response.status_code, 200)

    def test_logged_in_data_entry_user_can_access_account_list_page(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.account_list_url)

        self.assertEqual(response.status_code, 200)

    def test_logged_in_viewer_user_cannot_access_account_list_page(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.account_list_url)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_login_from_account_list_page(self):
        response = self.client.get(self.account_list_url)

        login_url = resolve_url(settings.LOGIN_URL)
        expected_redirect = f"{login_url}?next={self.account_list_url}"
        self.assertRedirects(
            response,
            expected_redirect,
            fetch_redirect_response=False,
        )

    def test_admin_can_access_account_create_page(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.account_create_url)

        self.assertEqual(response.status_code, 200)

    def test_data_entry_user_cannot_access_account_create_page(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.account_create_url)

        self.assertEqual(response.status_code, 403)

    def test_viewer_user_cannot_access_account_create_page(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.account_create_url)

        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_a_cash_account_with_post(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self.build_account_kwargs(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )

        response = self.client.post(self.account_create_url, data=payload)

        self.assertEqual(
            self.get_account_model().objects.count(),
            SEED_ACCOUNT_COUNT + 1,
        )
        self.assertTrue(
            self.get_account_model().objects.filter(
                name="Cash Account",
                account_type="cash",
                account_purpose="cash",
                currency="TRY",
            ).exists()
        )
        self.assertRedirects(response, self.account_list_url)

    def test_admin_can_create_an_online_donation_bank_account_with_post(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self.build_account_kwargs(
            name="Online Donation Bank Account",
            account_type="bank",
            account_purpose="online_donation",
            currency="TRY",
        )

        response = self.client.post(self.account_create_url, data=payload)

        self.assertEqual(
            self.get_account_model().objects.count(),
            SEED_ACCOUNT_COUNT + 1,
        )
        self.assertTrue(
            self.get_account_model().objects.filter(
                name="Online Donation Bank Account",
                account_type="bank",
                account_purpose="online_donation",
                currency="TRY",
            ).exists()
        )
        self.assertRedirects(response, self.account_list_url)

    def test_admin_can_create_a_main_expense_bank_account_with_post(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self.build_account_kwargs(
            name="Main Expense Bank Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )

        response = self.client.post(self.account_create_url, data=payload)

        self.assertEqual(
            self.get_account_model().objects.count(),
            SEED_ACCOUNT_COUNT + 1,
        )
        self.assertTrue(
            self.get_account_model().objects.filter(
                name="Main Expense Bank Account",
                account_type="bank",
                account_purpose="main_expense",
                currency="TRY",
            ).exists()
        )
        self.assertRedirects(response, self.account_list_url)

    def test_admin_can_create_a_usd_foreign_currency_account_with_post(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self.build_account_kwargs(
            name="USD Account",
            account_type="bank",
            account_purpose="foreign_currency",
            currency="USD",
        )

        response = self.client.post(self.account_create_url, data=payload)

        self.assertEqual(
            self.get_account_model().objects.count(),
            SEED_ACCOUNT_COUNT + 1,
        )
        self.assertTrue(
            self.get_account_model().objects.filter(
                name="USD Account",
                account_type="bank",
                account_purpose="foreign_currency",
                currency="USD",
            ).exists()
        )
        self.assertRedirects(response, self.account_list_url)

    def test_admin_can_create_a_savings_account_with_post(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self.build_account_kwargs(
            name="Savings Account",
            account_type="savings",
            account_purpose="savings",
            currency="TRY",
        )

        response = self.client.post(self.account_create_url, data=payload)

        self.assertEqual(
            self.get_account_model().objects.count(),
            SEED_ACCOUNT_COUNT + 1,
        )
        self.assertTrue(
            self.get_account_model().objects.filter(
                name="Savings Account",
                account_type="savings",
                account_purpose="savings",
                currency="TRY",
            ).exists()
        )
        self.assertRedirects(response, self.account_list_url)

    def test_after_successful_account_creation_user_is_redirected_to_account_list(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self.build_account_kwargs(
            name="Redirect Check Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )

        response = self.client.post(self.account_create_url, data=payload)

        self.assertRedirects(response, self.account_list_url)

    def test_admin_can_create_account_with_opening_balance(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self.build_account_kwargs(
            name="Opening Balance Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
            opening_balance=Decimal("2500.00"),
        )

        response = self.client.post(self.account_create_url, data=payload)

        self.assertTrue(
            self.get_account_model().objects.filter(
                name="Opening Balance Account",
                opening_balance=Decimal("2500.00"),
            ).exists()
        )
        self.assertRedirects(response, self.account_list_url)

    def test_account_list_displays_existing_accounts(self):
        self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.create_account(
            name="USD Account",
            account_type="bank",
            account_purpose="foreign_currency",
            currency="USD",
        )
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.account_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cash Account")
        self.assertContains(response, "USD Account")

    def test_account_list_displays_current_balances(self):
        from decimal import Decimal

        cash_account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
            opening_balance=Decimal("1000.00"),
        )
        income_category = self.create_category(name="Donation", category_type="income")
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("250.00"),
            target_account=cash_account,
            category=income_category,
            created_by=self.admin_user,
        )
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.account_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1250.00 TRY")

    def test_account_list_displays_empty_message_when_there_are_no_accounts(self):
        self.get_account_model().objects.all().delete()
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.account_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Henüz hesap bulunamadı.")
