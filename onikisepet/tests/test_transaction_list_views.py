from decimal import Decimal
import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.shortcuts import resolve_url
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from onikisepet.models import Receipt

from .helpers import TransactionTestMixin


class TransactionListViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        self.transaction_list_url = reverse("transaction_list")
        self.admin_user = self.create_user("transaction_list_admin", is_superuser=True)
        self.viewer_user = self.create_user("transaction_list_viewer", group_name="Viewer")

        self.cash_account = self.create_account(
            name="List Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.savings_account = self.create_account(
            name="List Savings Account",
            account_type="savings",
            account_purpose="savings",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="List Donation",
            category_type="income",
        )
        self.expense_category = self.create_category(
            name="List Rent",
            category_type="expense",
        )

    def _login_viewer(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

    def _create_income_transaction(self, **kwargs):
        defaults = {
            "date": "2026-06-10",
            "transaction_type": "income",
            "amount": Decimal("250.00"),
            "currency": "TRY",
            "target_account": self.cash_account,
            "category": self.income_category,
            "payee": "Anonymous Donor",
            "description": "Sunday offering",
            "created_by": self.admin_user,
        }
        defaults.update(kwargs)
        return self.get_transaction_model().objects.create(**defaults)

    def _create_cash_expense_transaction(self, **kwargs):
        defaults = {
            "date": "2026-06-12",
            "transaction_type": "expense",
            "amount": Decimal("75.50"),
            "currency": "TRY",
            "source_account": self.cash_account,
            "category": self.expense_category,
            "payee": "Local Market",
            "description": "Office supplies",
            "created_by": self.admin_user,
        }
        defaults.update(kwargs)
        return self.get_transaction_model().objects.create(**defaults)

    def _create_transfer_transaction(self, **kwargs):
        defaults = {
            "date": "2026-06-11",
            "transaction_type": "transfer",
            "amount": Decimal("100.00"),
            "currency": "TRY",
            "source_account": self.cash_account,
            "target_account": self.savings_account,
            "description": "Monthly savings transfer",
            "created_by": self.admin_user,
        }
        defaults.update(kwargs)
        return self.get_transaction_model().objects.create(**defaults)

    def _create_receipt(self, transaction):
        return Receipt.objects.create(
            transaction=transaction,
            file=SimpleUploadedFile(
                "list-receipt.pdf",
                b"receipt content",
                content_type="application/pdf",
            ),
            original_filename="list-receipt.pdf",
            uploaded_by=self.admin_user,
        )

    def test_transaction_list_displays_transaction_fields(self):
        self._create_income_transaction()
        self._login_viewer()

        response = self.client.get(self.transaction_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2026-06-10")
        self.assertContains(response, "Income")
        self.assertContains(response, "250.00")
        self.assertContains(response, "TRY")
        self.assertContains(response, "Anonymous Donor")
        self.assertContains(response, "List Cash Account")
        self.assertContains(response, "List Donation")
        self.assertContains(response, "Sunday offering")

    def test_transaction_list_displays_source_and_target_accounts_for_transfer(self):
        self._create_transfer_transaction()
        self._login_viewer()

        response = self.client.get(self.transaction_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Transfer")
        self.assertContains(response, "List Cash Account")
        self.assertContains(response, "List Savings Account")
        self.assertContains(response, "Monthly savings transfer")

    def test_transaction_list_orders_transactions_by_date_newest_first(self):
        older_transaction = self._create_income_transaction(
            date="2026-01-05",
            description="Older transaction",
        )
        newer_transaction = self._create_cash_expense_transaction(
            date="2026-06-20",
            description="Newer transaction",
        )
        self._login_viewer()

        response = self.client.get(self.transaction_list_url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertLess(
            content.index(newer_transaction.date.isoformat()),
            content.index(older_transaction.date.isoformat()),
        )

    def test_transaction_list_shows_receipt_download_link_for_cash_expense_with_receipt(self):
        cash_expense = self._create_cash_expense_transaction()
        receipt = self._create_receipt(cash_expense)
        receipt_url = reverse("receipt_download", kwargs={"pk": receipt.pk})
        self._login_viewer()

        response = self.client.get(self.transaction_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{receipt_url}"')
        self.assertContains(response, "Fiş İndir")

    def test_transaction_list_leaves_receipt_cell_empty_without_receipt(self):
        self._create_cash_expense_transaction(description="Receiptless cash expense")
        self._create_income_transaction(description="Income without receipt")
        self._login_viewer()

        response = self.client.get(self.transaction_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("receipt_download", kwargs={"pk": 1}))
        self.assertNotContains(response, "Fiş İndir")

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.transaction_list_url)

        login_url = resolve_url(settings.LOGIN_URL)
        self.assertRedirects(
            response,
            f"{login_url}?next={self.transaction_list_url}",
            fetch_redirect_response=False,
        )

    def test_transaction_list_avoids_n_plus_one_queries(self):
        first_expense = self._create_cash_expense_transaction(date="2026-06-01")
        self._create_receipt(first_expense)
        self._create_transfer_transaction(date="2026-06-02")
        self._create_income_transaction(date="2026-06-03")
        self._login_viewer()

        with CaptureQueriesContext(connection) as single_transaction_queries:
            self.client.get(self.transaction_list_url)

        for extra_day in range(4, 9):
            expense = self._create_cash_expense_transaction(
                date=f"2026-06-0{extra_day}",
                description=f"Bulk expense {extra_day}",
                payee=f"Vendor {extra_day}",
            )
            self._create_receipt(expense)

        with CaptureQueriesContext(connection) as many_transaction_queries:
            self.client.get(self.transaction_list_url)

        self.assertEqual(
            len(single_transaction_queries),
            len(many_transaction_queries),
        )
