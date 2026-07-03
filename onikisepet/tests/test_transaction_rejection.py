from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from onikisepet.models import Transaction

from .helpers import ProfileTestMixin, TransactionTestMixin


class TransactionRejectionTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def setUp(self):
        self.admin_user = self.create_user("reject_admin", is_superuser=True)
        self.data_entry_user = self.create_user_with_profile(
            "reject_data_entry",
            role=self.ROLE_DATA_ENTRY,
        )
        self.cash_account = self.create_account(
            name="Reject Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Reject Income",
            category_type="income",
        )
        self.pending_transaction = self.create_transaction(
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.data_entry_user,
            approval_status=Transaction.ApprovalStatus.PENDING,
        )

    def test_reject_without_reason_returns_form_error(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            reverse("transaction_reject", kwargs={"pk": self.pending_transaction.pk}),
            data={},
        )

        self.assertEqual(response.status_code, 200)
        self.pending_transaction.refresh_from_db()
        self.assertEqual(
            self.pending_transaction.approval_status,
            Transaction.ApprovalStatus.PENDING,
        )

    def test_rejected_transaction_cannot_be_approved(self):
        self.pending_transaction.approval_status = Transaction.ApprovalStatus.REJECTED
        self.pending_transaction.rejection_reason = "Kapatıldı"
        self.pending_transaction.save(
            update_fields=["approval_status", "rejection_reason", "updated_at"]
        )
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            reverse("transaction_approve", kwargs={"pk": self.pending_transaction.pk}),
        )

        self.assertRedirects(response, reverse("transaction_list"))
        self.pending_transaction.refresh_from_db()
        self.assertEqual(
            self.pending_transaction.approval_status,
            Transaction.ApprovalStatus.REJECTED,
        )

    def test_rejected_transaction_edit_returns_403(self):
        self.pending_transaction.approval_status = Transaction.ApprovalStatus.REJECTED
        self.pending_transaction.rejection_reason = "Kapatıldı"
        self.pending_transaction.save(
            update_fields=["approval_status", "rejection_reason", "updated_at"]
        )
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(
            reverse("transaction_edit", kwargs={"pk": self.pending_transaction.pk}),
        )

        self.assertEqual(response.status_code, 403)
