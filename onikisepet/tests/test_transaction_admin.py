from decimal import Decimal

from django.contrib import admin
from django.test import RequestFactory, TestCase

from onikisepet.models import Transaction

from .helpers import TransactionTestMixin


class TransactionAdminTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("admin_user", is_superuser=True)
        self.cash_account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
            opening_balance=Decimal("1000.00"),
        )
        self.bank_account = self.create_account(
            name="Bank Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
            opening_balance=Decimal("500.00"),
        )
        self.income_category = self.create_category(
            name="Donation",
            category_type="income",
        )

    def get_transaction_admin(self):
        transaction_model = self.get_transaction_model()
        return admin.site._registry[transaction_model]

    def test_transaction_model_is_registered_in_admin(self):
        transaction_model = self.get_transaction_model()
        self.assertIn(transaction_model, admin.site._registry)

    def test_transaction_admin_list_display_contains_expected_fields(self):
        transaction_admin = self.get_transaction_admin()

        expected_fields = [
            "date",
            "transaction_type",
            "payee",
            "amount",
            "currency",
            "source_account",
            "target_account",
            "category",
            "approval_status",
            "approved_by",
            "created_by",
            "created_at",
            "updated_at",
        ]

        self.assertEqual(list(transaction_admin.list_display), expected_fields)

    def test_transaction_admin_list_filter_contains_expected_fields(self):
        transaction_admin = self.get_transaction_admin()

        expected_filters = [
            "transaction_type",
            "approval_status",
            "currency",
            "date",
            "category",
            "source_account",
            "target_account",
            "created_by",
        ]

        self.assertEqual(list(transaction_admin.list_filter), expected_filters)

    def test_transaction_admin_search_fields_contains_expected_fields(self):
        transaction_admin = self.get_transaction_admin()

        expected_search = [
            "payee",
            "description",
            "source_account__name",
            "target_account__name",
            "category__name",
            "created_by__username",
        ]

        self.assertEqual(list(transaction_admin.search_fields), expected_search)

    def test_transaction_admin_orders_by_date_and_created_at(self):
        transaction_admin = self.get_transaction_admin()

        self.assertEqual(list(transaction_admin.ordering), ["-date", "-created_at"])

    def test_transaction_admin_readonly_fields_contains_timestamps_and_approved_at(self):
        transaction_admin = self.get_transaction_admin()

        self.assertEqual(
            list(transaction_admin.readonly_fields),
            ["created_at", "updated_at", "approved_at"],
        )

    def test_transaction_admin_disallows_delete(self):
        transaction_admin = self.get_transaction_admin()

        self.assertFalse(transaction_admin.has_delete_permission(None))

    def test_transaction_admin_save_model_sets_created_by_for_superuser_when_missing(self):
        transaction_model = self.get_transaction_model()
        transaction = transaction_model(
            date="2026-05-30",
            transaction_type="income",
            amount=Decimal("100.00"),
            currency="TRY",
            target_account=self.cash_account,
            category=self.income_category,
        )

        request = RequestFactory().get("/admin/onikisepet/transaction/add/")
        request.user = self.user

        transaction_admin = self.get_transaction_admin()
        transaction_admin.save_model(request, transaction, form=None, change=False)

        self.assertEqual(transaction.created_by, self.user)
        self.assertEqual(transaction.approval_status, Transaction.ApprovalStatus.APPROVED)

    def test_transaction_admin_save_model_sets_transfer_to_pending(self):
        transaction_model = self.get_transaction_model()
        transaction = transaction_model(
            date="2026-05-30",
            transaction_type="transfer",
            amount=Decimal("100.00"),
            currency="TRY",
            source_account=self.cash_account,
            target_account=self.bank_account,
        )

        request = RequestFactory().get("/admin/onikisepet/transaction/add/")
        request.user = self.user

        transaction_admin = self.get_transaction_admin()
        transaction_admin.save_model(request, transaction, form=None, change=False)

        self.assertEqual(transaction.created_by, self.user)
        self.assertEqual(transaction.approval_status, Transaction.ApprovalStatus.PENDING)
