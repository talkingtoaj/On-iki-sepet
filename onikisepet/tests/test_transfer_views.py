from decimal import Decimal

from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse

from onikisepet.models import Receipt

from .helpers import TransactionTestMixin


class TransferViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.transfer_create_url = reverse("transfer_create")
        self.transaction_list_url = reverse("transaction_list")

        self.admin_user = self.create_user("transfer_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "transfer_data_entry",
            group_name="Data Entry",
        )
        self.viewer_user = self.create_user("transfer_viewer", group_name="Viewer")

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
        self.usd_bank_account = self.create_account(
            name="USD Bank Account",
            account_type="bank",
            account_purpose="foreign_currency",
            currency="USD",
        )

    def _valid_payload(self, *, source_account=None, target_account=None):
        return {
            "date": "2026-06-13",
            "amount": "150.75",
            "source_account": (source_account or self.cash_account).pk,
            "target_account": (target_account or self.bank_account).pk,
            "description": "Move cash to bank",
        }

    def _transaction_model(self):
        return self.get_transaction_model()

    def test_admin_can_access_transfer_create_page(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.transfer_create_url)

        self.assertEqual(response.status_code, 200)

    def test_data_entry_can_access_transfer_create_page(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.transfer_create_url)

        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_access_transfer_create_page(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.transfer_create_url)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.transfer_create_url)

        login_url = resolve_url(settings.LOGIN_URL)
        expected_redirect = f"{login_url}?next={self.transfer_create_url}"
        self.assertRedirects(
            response,
            expected_redirect,
            fetch_redirect_response=False,
        )

    def test_admin_can_create_transfer(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(self.transfer_create_url, data=self._valid_payload())

        self.assertEqual(self._transaction_model().objects.count(), 1)
        transaction = self._transaction_model().objects.get()
        self.assertEqual(transaction.transaction_type, "transfer")
        self.assertEqual(transaction.source_account, self.cash_account)
        self.assertEqual(transaction.target_account, self.bank_account)
        self.assertIsNone(transaction.category)
        self.assertEqual(transaction.payee, "")
        self.assertEqual(transaction.amount, Decimal("150.75"))
        self.assertEqual(transaction.description, "Move cash to bank")

    def test_data_entry_can_create_transfer(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        self.client.post(self.transfer_create_url, data=self._valid_payload())

        self.assertEqual(self._transaction_model().objects.count(), 1)

    def test_transfer_create_sets_transaction_created_by(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(self.transfer_create_url, data=self._valid_payload())

        transaction = self._transaction_model().objects.get()
        self.assertEqual(transaction.created_by, self.admin_user)

    def test_transfer_create_uses_source_account_currency(self):
        usd_target_account = self.create_account(
            name="USD Savings Account",
            account_type="savings",
            account_purpose="savings",
            currency="USD",
        )
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(
            self.transfer_create_url,
            data=self._valid_payload(
                source_account=self.usd_bank_account,
                target_account=usd_target_account,
            ),
        )

        transaction = self._transaction_model().objects.get()
        self.assertEqual(transaction.currency, "USD")

    def test_transfer_create_sets_category_to_none(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(self.transfer_create_url, data=self._valid_payload())

        transaction = self._transaction_model().objects.get()
        self.assertIsNone(transaction.category)

    def test_transfer_create_sets_payee_to_empty_string(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(self.transfer_create_url, data=self._valid_payload())

        transaction = self._transaction_model().objects.get()
        self.assertEqual(transaction.payee, "")

    def test_transfer_create_does_not_create_receipt(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(self.transfer_create_url, data=self._valid_payload())

        self.assertEqual(self._transaction_model().objects.count(), 1)
        self.assertEqual(Receipt.objects.count(), 0)

    def test_successful_transfer_create_redirects_to_transaction_list(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            self.transfer_create_url,
            data=self._valid_payload(),
        )

        self.assertRedirects(response, self.transaction_list_url)

    def test_invalid_form_does_not_create_transaction(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self._valid_payload()
        payload.pop("source_account")

        response = self.client.post(self.transfer_create_url, data=payload)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "source_account",
            "This field is required.",
        )
        self.assertEqual(self._transaction_model().objects.count(), 0)

    def test_transfer_create_rejects_same_source_and_target_account(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            self.transfer_create_url,
            data=self._valid_payload(target_account=self.cash_account),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "target_account",
            "Transfer accounts must be different.",
        )
        self.assertEqual(self._transaction_model().objects.count(), 0)

    def test_transfer_create_rejects_cross_currency_transfer(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            self.transfer_create_url,
            data=self._valid_payload(target_account=self.usd_bank_account),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "target_account",
            "Cross-currency transfers are not supported in the MVP.",
        )
        self.assertEqual(self._transaction_model().objects.count(), 0)
