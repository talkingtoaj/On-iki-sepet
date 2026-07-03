from decimal import Decimal

from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse

from onikisepet.models import Receipt

from .helpers import TransactionTestMixin


class OnlineDonationIncomeViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.online_donation_income_create_url = reverse(
            "online_donation_income_create"
        )
        self.transaction_list_url = reverse("transaction_list")

        self.admin_user = self.create_user(
            "online_donation_admin",
            is_superuser=True,
        )
        self.data_entry_user = self.create_user(
            "online_donation_data_entry",
            group_name="Data Entry",
        )
        self.viewer_user = self.create_user(
            "online_donation_viewer",
            group_name="Viewer",
        )

        self.online_donation_account = self.create_account(
            name="Online Donation Bank Account",
            account_type="bank",
            account_purpose="online_donation",
            currency="TRY",
        )
        self.usd_online_donation_account = self.create_account(
            name="USD Online Donation Bank Account",
            account_type="bank",
            account_purpose="online_donation",
            currency="USD",
        )
        self.income_category = self.create_category(
            name="Online Donation",
            category_type="income",
        )

    def _valid_payload(self, *, online_donation_account=None, donor_name="Jane Donor"):
        return {
            "date": "2026-06-13",
            "donor_name": donor_name,
            "amount": "450.25",
            "online_donation_account": (
                online_donation_account or self.online_donation_account
            ).pk,
            "category": self.income_category.pk,
            "description": "Online giving platform donation",
        }

    def _transaction_model(self):
        return self.get_transaction_model()

    def test_admin_can_access_online_donation_income_create_page(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.online_donation_income_create_url)

        self.assertEqual(response.status_code, 200)

    def test_data_entry_can_access_online_donation_income_create_page(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.online_donation_income_create_url)

        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_access_online_donation_income_create_page(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.online_donation_income_create_url)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.online_donation_income_create_url)

        login_url = resolve_url(settings.LOGIN_URL)
        expected_redirect = f"{login_url}?next={self.online_donation_income_create_url}"
        self.assertRedirects(
            response,
            expected_redirect,
            fetch_redirect_response=False,
        )

    def test_admin_can_create_online_donation_income(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(
            self.online_donation_income_create_url,
            data=self._valid_payload(),
        )

        self.assertEqual(self._transaction_model().objects.count(), 1)
        transaction = self._transaction_model().objects.get()
        self.assertEqual(transaction.transaction_type, "income")
        self.assertIsNone(transaction.source_account)  # type: ignore[attr-defined]
        self.assertEqual(transaction.target_account, self.online_donation_account)  # type: ignore[attr-defined]
        self.assertEqual(transaction.category, self.income_category)
        self.assertEqual(transaction.payee, "Jane Donor")
        self.assertEqual(transaction.amount, Decimal("450.25"))
        self.assertEqual(transaction.description, "Online giving platform donation")

    def test_data_entry_can_create_online_donation_income(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        self.client.post(
            self.online_donation_income_create_url,
            data=self._valid_payload(),
        )

        self.assertEqual(self._transaction_model().objects.count(), 1)

    def test_online_donation_income_create_sets_transaction_created_by(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(
            self.online_donation_income_create_url,
            data=self._valid_payload(),
        )

        transaction = self._transaction_model().objects.get()
        self.assertEqual(transaction.created_by, self.admin_user)

    def test_online_donation_income_create_uses_online_donation_account_currency(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(
            self.online_donation_income_create_url,
            data=self._valid_payload(
                online_donation_account=self.usd_online_donation_account,
            ),
        )

        transaction = self._transaction_model().objects.get()
        self.assertEqual(transaction.currency, "USD")

    def test_online_donation_income_create_maps_donor_name_to_payee(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(
            self.online_donation_income_create_url,
            data=self._valid_payload(donor_name="Vahan"),
        )

        transaction = self._transaction_model().objects.get()
        self.assertEqual(transaction.payee, "Vahan")

    def test_online_donation_income_create_does_not_create_receipt(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(
            self.online_donation_income_create_url,
            data=self._valid_payload(),
        )

        self.assertEqual(self._transaction_model().objects.count(), 1)
        self.assertEqual(Receipt.objects.count(), 0)

    def test_successful_online_donation_income_create_redirects_to_transaction_list(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            self.online_donation_income_create_url,
            data=self._valid_payload(),
        )

        self.assertRedirects(response, self.transaction_list_url)

    def test_invalid_form_does_not_create_transaction(self):
        self.client.login(username=self.admin_user.username, password=self.password)
        payload = self._valid_payload()
        payload.pop("online_donation_account")

        response = self.client.post(
            self.online_donation_income_create_url,
            data=payload,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "online_donation_account",
            "Bu alan zorunludur.",
        )
        self.assertEqual(self._transaction_model().objects.count(), 0)
