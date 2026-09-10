import tempfile
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from onikisepet.usecases.roles import DATA_ENTRY, TREASURER, VIEWER

from .helpers import ReceiptFileTestMixin, TransactionTestMixin


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ViewPermissionMatrixTests(
    ReceiptFileTestMixin, TransactionTestMixin, TestCase
):
    """Church books include donor records, so reading is a granted permission
    too, not merely a matter of holding any account. Writing is separated
    further: data entry may post transactions but may not reshape the chart of
    accounts or move exchange rates, both of which change reported figures.
    """

    def setUp(self):
        self.treasurer = self.create_user("perm_treasurer", group_name=TREASURER)
        self.data_entry = self.create_user("perm_data_entry", group_name=DATA_ENTRY)
        self.viewer = self.create_user("perm_viewer", group_name=VIEWER)
        self.no_role = self.create_user("perm_no_role")

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
        self.expense_category = self.create_category(
            name="Supplies",
            category_type="expense",
        )
        self.transaction = self.create_transaction(
            transaction_type="expense",
            amount=Decimal("60.00"),
            source_account=self.cash_account,
            category=self.expense_category,
            created_by=self.treasurer,
        )

    def _login(self, user):
        self.client.login(username=user.username, password=self.password)

    def _status(self, user, url_name, args=None):
        self._login(user)
        return self.client.get(reverse(url_name, args=args or [])).status_code

    # --- read access ------------------------------------------------------

    def test_all_three_roles_can_read_every_list(self):
        for url_name in [
            "report_dashboard",
            "transaction_list",
            "account_list",
            "category_list",
            "exchange_rate_list",
        ]:
            for user in [self.treasurer, self.data_entry, self.viewer]:
                self.assertEqual(
                    self._status(user, url_name),
                    200,
                    f"{user.username} should read {url_name}",
                )

    def test_all_three_roles_can_read_a_transaction_detail(self):
        for user in [self.treasurer, self.data_entry, self.viewer]:
            self.assertEqual(
                self._status(user, "transaction_detail", [self.transaction.pk]),
                200,
            )

    def test_a_user_with_no_role_cannot_read_the_books(self):
        for url_name in [
            "report_dashboard",
            "transaction_list",
            "account_list",
            "exchange_rate_list",
        ]:
            self.assertEqual(
                self._status(self.no_role, url_name),
                403,
                f"role-less user should not read {url_name}",
            )

    # --- write access -----------------------------------------------------

    def test_only_the_treasurer_can_open_the_account_form(self):
        self.assertEqual(self._status(self.treasurer, "account_create"), 200)
        self.assertEqual(self._status(self.data_entry, "account_create"), 403)
        self.assertEqual(self._status(self.viewer, "account_create"), 403)

    def test_only_the_treasurer_can_open_the_category_form(self):
        self.assertEqual(self._status(self.treasurer, "category_create"), 200)
        self.assertEqual(self._status(self.data_entry, "category_create"), 403)
        self.assertEqual(self._status(self.viewer, "category_create"), 403)

    def test_only_the_treasurer_can_open_the_exchange_rate_form(self):
        self.assertEqual(self._status(self.treasurer, "exchange_rate_create"), 200)
        self.assertEqual(self._status(self.data_entry, "exchange_rate_create"), 403)
        self.assertEqual(self._status(self.viewer, "exchange_rate_create"), 403)

    def test_treasurer_and_data_entry_can_open_the_transaction_form(self):
        self.assertEqual(self._status(self.treasurer, "transaction_create"), 200)
        self.assertEqual(self._status(self.data_entry, "transaction_create"), 200)
        self.assertEqual(self._status(self.viewer, "transaction_create"), 403)

    def test_treasurer_and_data_entry_can_open_the_cash_expense_form(self):
        self.assertEqual(self._status(self.treasurer, "cash_expense_create"), 200)
        self.assertEqual(self._status(self.data_entry, "cash_expense_create"), 200)
        self.assertEqual(self._status(self.viewer, "cash_expense_create"), 403)

    def test_viewer_posting_a_transaction_is_refused_and_writes_nothing(self):
        before = self.get_transaction_model().objects.count()
        self._login(self.viewer)

        response = self.client.post(
            reverse("transaction_create"),
            {
                "date": "2026-09-09",
                "amount": "10.00",
                "transaction_type": "income",
                "account": self.cash_account.pk,
                "category": self.income_category.pk,
                "description": "Should not be saved",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.get_transaction_model().objects.count(), before)

    def test_data_entry_posting_an_account_is_refused_and_writes_nothing(self):
        before = self.get_account_model().objects.count()
        self._login(self.data_entry)

        response = self.client.post(
            reverse("account_create"),
            {
                "name": "Sneaky Account",
                "account_type": "bank",
                "account_purpose": "savings",
                "currency": "TRY",
                "opening_balance": "0.00",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.get_account_model().objects.count(), before)
