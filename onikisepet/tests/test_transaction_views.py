from decimal import Decimal
from typing import Any

from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse

from .helpers import TransactionTestMixin


class TransactionViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.transaction_list_url = reverse("transaction_list")
        self.transaction_create_url = reverse("transaction_create")

        self.admin_user = self.create_user("transaction_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "transaction_data_entry",
            group_name="Data Entry",
        )
        self.viewer_user = self.create_user("transaction_viewer", group_name="Viewer")

        self.cash_account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.bank_account = self.create_account(
            name="Main Bank Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Donation",
            category_type="income",
        )
        self.expense_category = self.create_category(
            name="Rent",
            category_type="expense",
        )

    def _build_post_data(
        self,
        *,
        date="2026-05-30",
        amount: str | None = "10.00",
        transaction_type="income",
        account=None,
        source_account=None,
        target_account=None,
        category=None,
        payee=None,
        description="Test transaction",
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
            "date": date,
            "transaction_type": transaction_type,
            "description": description,
        }
        if amount is not None:
            data["amount"] = amount
        if account is not None:
            data["account"] = account.pk
        if source_account is not None:
            data["source_account"] = source_account.pk
        if target_account is not None:
            data["target_account"] = target_account.pk
        if category is not None:
            data["category"] = category.pk
        if payee is not None:
            data["payee"] = payee
        return data

    def test_logged_in_admin_can_access_transaction_list_page(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.transaction_list_url)

        self.assertEqual(response.status_code, 200)

    def test_logged_in_data_entry_user_can_access_transaction_list_page(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.transaction_list_url)

        self.assertEqual(response.status_code, 200)

    def test_logged_in_viewer_user_can_access_transaction_list_page(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.transaction_list_url)

        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected_to_login_from_transaction_list_page(self):
        response = self.client.get(self.transaction_list_url)

        login_url = resolve_url(settings.LOGIN_URL)
        expected_redirect = f"{login_url}?next={self.transaction_list_url}"
        self.assertRedirects(
            response,
            expected_redirect,
            fetch_redirect_response=False,
        )

    def test_admin_can_access_transaction_create_page(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.transaction_create_url)

        self.assertEqual(response.status_code, 200)

    def test_data_entry_user_can_access_transaction_create_page(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.transaction_create_url)

        self.assertEqual(response.status_code, 200)

    def test_viewer_user_cannot_access_transaction_create_page(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.transaction_create_url)

        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_income_transaction_with_post(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self._build_post_data(
            transaction_type="income",
            account=self.cash_account,
            category=self.income_category,
            description="Sunday donation",
        )

        response = self.client.post(self.transaction_create_url, data=payload)

        self.assertTrue(
            self.get_transaction_model().objects.filter(
                transaction_type="income",
                target_account=self.cash_account,
                category=self.income_category,
            ).exists()
        )
        self.assertRedirects(response, self.transaction_list_url)

    def test_data_entry_user_can_create_expense_transaction_with_post(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)
        payload = self._build_post_data(
            transaction_type="expense",
            account=self.cash_account,
            category=self.expense_category,
            description="Rent payment",
        )

        response = self.client.post(self.transaction_create_url, data=payload)

        self.assertTrue(
            self.get_transaction_model().objects.filter(
                transaction_type="expense",
                source_account=self.cash_account,
                category=self.expense_category,
            ).exists()
        )
        self.assertRedirects(response, self.transaction_list_url)

    def test_admin_can_create_transfer_transaction_with_post(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self._build_post_data(
            transaction_type="transfer",
            source_account=self.cash_account,
            target_account=self.bank_account,
            description="Move cash to bank",
        )

        response = self.client.post(self.transaction_create_url, data=payload)

        self.assertTrue(
            self.get_transaction_model().objects.filter(
                transaction_type="transfer",
                source_account=self.cash_account,
                target_account=self.bank_account,
                category__isnull=True,
            ).exists()
        )
        self.assertRedirects(response, self.transaction_list_url)

    def test_admin_can_create_transaction_with_payee(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self._build_post_data(
            transaction_type="expense",
            account=self.cash_account,
            category=self.expense_category,
            payee="Migros",
            description="Groceries",
        )

        response = self.client.post(self.transaction_create_url, data=payload)

        self.assertTrue(
            self.get_transaction_model().objects.filter(
                transaction_type="expense",
                payee="Migros",
                source_account=self.cash_account,
            ).exists()
        )
        self.assertRedirects(response, self.transaction_list_url)

    def test_data_entry_can_create_transaction_with_payee(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)
        payload = self._build_post_data(
            transaction_type="expense",
            account=self.cash_account,
            category=self.expense_category,
            payee="Vahan",
            description="Cash reimbursement",
        )

        response = self.client.post(self.transaction_create_url, data=payload)

        self.assertTrue(
            self.get_transaction_model().objects.filter(
                transaction_type="expense",
                payee="Vahan",
                created_by=self.data_entry_user,
            ).exists()
        )
        self.assertRedirects(response, self.transaction_list_url)

    def test_transaction_create_still_works_without_payee(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self._build_post_data(
            transaction_type="income",
            account=self.cash_account,
            category=self.income_category,
        )

        response = self.client.post(self.transaction_create_url, data=payload)

        self.assertTrue(
            self.get_transaction_model().objects.filter(
                transaction_type="income",
                target_account=self.cash_account,
            ).exists()
        )
        self.assertRedirects(response, self.transaction_list_url)

    def test_created_by_is_automatically_set_to_logged_in_user_when_admin_creates_transaction(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self._build_post_data(
            transaction_type="income",
            account=self.cash_account,
            category=self.income_category,
        )

        self.client.post(self.transaction_create_url, data=payload)

        transaction = self.get_transaction_model().objects.get()
        self.assertEqual(getattr(transaction, "created_by"), self.admin_user)

    def test_created_by_is_automatically_set_to_logged_in_user_when_data_entry_creates_transaction(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)
        payload = self._build_post_data(
            transaction_type="expense",
            account=self.cash_account,
            category=self.expense_category,
        )

        self.client.post(self.transaction_create_url, data=payload)

        transaction = self.get_transaction_model().objects.get()
        self.assertEqual(getattr(transaction, "created_by"), self.data_entry_user)

    def test_user_does_not_manually_submit_currency_currency_is_saved_from_selected_account(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self._build_post_data(
            transaction_type="income",
            account=self.cash_account,
            category=self.income_category,
        )

        self.client.post(self.transaction_create_url, data=payload)

        transaction = self.get_transaction_model().objects.get()
        self.assertEqual(getattr(transaction, "currency"), "TRY")

    def test_after_successful_transaction_creation_user_is_redirected_to_transaction_list(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self._build_post_data(
            transaction_type="income",
            account=self.cash_account,
            category=self.income_category,
        )

        response = self.client.post(self.transaction_create_url, data=payload)

        self.assertRedirects(response, self.transaction_list_url)

    def test_transaction_list_displays_existing_transactions(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=self.cash_account,
            category=self.income_category,
            description="Sunday donation",
            created_by=self.admin_user,
        )
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.transaction_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sunday donation")

    def test_transaction_list_displays_empty_message_when_there_are_no_transactions(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.transaction_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Henüz işlem bulunamadı.")
