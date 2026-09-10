# These tests assert the English wording of the interface. The app now
# defaults to Turkish, so the language is pinned here rather than left
# implicit; Turkish rendering is covered in test_localization.py.
import tempfile
from decimal import Decimal

from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase, override_settings
from django.urls import reverse

from .helpers import ReceiptFileTestMixin, TransactionTestMixin


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(), LANGUAGE_CODE="en")
class TransactionDetailViewTests(
    ReceiptFileTestMixin, TransactionTestMixin, TestCase
):
    """Uploaded receipts previously had nowhere to be seen in the app itself."""

    def setUp(self):
        self.user = self.create_user("detail_user", is_superuser=True)
        self.cash_account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.expense_category = self.create_category(
            name="Supplies",
            category_type="expense",
        )
        self.transaction = self.create_transaction(
            transaction_type="expense",
            amount=Decimal("125.00"),
            source_account=self.cash_account,
            category=self.expense_category,
            description="Office supplies",
            created_by=self.user,
        )
        self.url = reverse("transaction_detail", args=[self.transaction.pk])

    def _attach_receipt(self):
        from onikisepet.models import Receipt

        uploaded = self.make_receipt_file("receipt.jpg")
        return Receipt.objects.create(
            transaction=self.transaction,
            file=uploaded,
            original_filename=uploaded.name,
            uploaded_by=self.user,
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url)

        login_url = resolve_url(settings.LOGIN_URL)
        self.assertRedirects(
            response,
            f"{login_url}?next={self.url}",
            fetch_redirect_response=False,
        )

    def test_detail_page_shows_the_transaction(self):
        self.client.login(username=self.user.username, password=self.password)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Office supplies")
        self.assertContains(response, "125.00")
        self.assertContains(response, "TRY")
        self.assertContains(response, "Cash Account")

    def test_detail_page_links_to_an_attached_receipt(self):
        receipt = self._attach_receipt()
        self.client.login(username=self.user.username, password=self.password)

        response = self.client.get(self.url)

        self.assertContains(response, receipt.file.url)
        self.assertContains(response, "receipt.jpg")

    def test_detail_page_states_when_there_are_no_receipts(self):
        self.client.login(username=self.user.username, password=self.password)

        response = self.client.get(self.url)

        self.assertContains(response, "No receipts")

    def test_unknown_transaction_returns_404(self):
        self.client.login(username=self.user.username, password=self.password)

        response = self.client.get(reverse("transaction_detail", args=[999999]))

        self.assertEqual(response.status_code, 404)

    def test_transaction_list_links_to_the_detail_page(self):
        self.client.login(username=self.user.username, password=self.password)

        response = self.client.get(reverse("transaction_list"))

        self.assertContains(response, self.url)
