from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from onikisepet.models import AuditLog, Transaction
from onikisepet.usecases import approval

from .helpers import ProfileTestMixin, TransactionTestMixin


class BulkApproveUseCaseTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def setUp(self):
        self.admin_user = self.create_user("bulk_approve_admin", is_superuser=True)
        self.cash_account = self.create_account(
            name="Bulk Approve Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Bulk Approve Income",
            category_type="income",
        )

    def test_bulk_approve_approves_only_pending_transactions(self):
        pending_one = self.create_transaction(
            transaction_type="income",
            amount=Decimal("10.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.admin_user,
            approval_status=Transaction.ApprovalStatus.PENDING,
        )
        pending_two = self.create_transaction(
            transaction_type="income",
            amount=Decimal("20.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.admin_user,
            approval_status=Transaction.ApprovalStatus.PENDING,
        )
        approved = self.create_transaction(
            transaction_type="income",
            amount=Decimal("30.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.admin_user,
            approval_status=Transaction.ApprovalStatus.APPROVED,
        )

        count = approval.bulk_approve_transactions(
            user=self.admin_user,
            transaction_ids=[pending_one.pk, pending_two.pk, approved.pk],
        )

        self.assertEqual(count, 2)
        pending_one.refresh_from_db()
        pending_two.refresh_from_db()
        approved.refresh_from_db()
        self.assertEqual(pending_one.approval_status, Transaction.ApprovalStatus.APPROVED)
        self.assertEqual(pending_two.approval_status, Transaction.ApprovalStatus.APPROVED)
        self.assertEqual(approved.approval_status, Transaction.ApprovalStatus.APPROVED)

    def test_bulk_approve_returns_zero_for_empty_selection(self):
        count = approval.bulk_approve_transactions(
            user=self.admin_user,
            transaction_ids=[],
        )

        self.assertEqual(count, 0)


class TransactionBulkApproveViewTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def setUp(self):
        self.bulk_approve_url = reverse("transaction_bulk_approve")
        self.transaction_list_url = reverse("transaction_list")
        self.admin_user = self.create_user("bulk_approve_view_admin", is_superuser=True)
        self.approver_user = self.create_data_entry_approver("bulk_approve_view_approver")
        self.data_entry_user = self.create_user_with_profile(
            "bulk_approve_view_data_entry",
            role=self.ROLE_DATA_ENTRY,
        )
        self.cash_account = self.create_account(
            name="Bulk Approve View Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Bulk Approve View Income",
            category_type="income",
        )

    def _create_pending(self, *, amount, description=""):
        return self.create_transaction(
            transaction_type="income",
            amount=Decimal(amount),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.data_entry_user,
            approval_status=Transaction.ApprovalStatus.PENDING,
            description=description,
        )

    def test_data_entry_cannot_bulk_approve(self):
        pending = self._create_pending(amount="100.00")
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.post(
            self.bulk_approve_url,
            data={"transaction_ids": [pending.pk]},
        )

        self.assertEqual(response.status_code, 403)
        pending.refresh_from_db()
        self.assertEqual(pending.approval_status, Transaction.ApprovalStatus.PENDING)

    def test_admin_can_bulk_approve_selected_transactions(self):
        first = self._create_pending(amount="100.00", description="Bulk one")
        second = self._create_pending(amount="200.00", description="Bulk two")
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            self.bulk_approve_url,
            data={
                "transaction_ids": [first.pk, second.pk],
            },
        )

        self.assertRedirects(response, self.transaction_list_url)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.approval_status, Transaction.ApprovalStatus.APPROVED)
        self.assertEqual(second.approval_status, Transaction.ApprovalStatus.APPROVED)

    def test_approver_can_bulk_approve_selected_transactions(self):
        pending = self._create_pending(amount="150.00")
        self.client.login(username=self.approver_user.username, password=self.password)

        response = self.client.post(
            self.bulk_approve_url,
            data={"transaction_ids": [pending.pk]},
        )

        self.assertRedirects(response, self.transaction_list_url)
        pending.refresh_from_db()
        self.assertEqual(pending.approval_status, Transaction.ApprovalStatus.APPROVED)

    def test_bulk_approve_preserves_list_filters_in_redirect(self):
        pending = self._create_pending(amount="100.00")
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            self.bulk_approve_url,
            data={
                "transaction_ids": [pending.pk],
                "status": "pending",
                "mine": "1",
            },
        )

        self.assertRedirects(
            response,
            f"{self.transaction_list_url}?status=pending&mine=1",
        )

    def test_bulk_approve_logs_audit_entry_for_each_transaction(self):
        first = self._create_pending(amount="100.00")
        second = self._create_pending(amount="200.00")
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(
            self.bulk_approve_url,
            data={"transaction_ids": [first.pk, second.pk]},
        )

        self.assertEqual(
            AuditLog.objects.filter(
                content_type="transaction",
                action=AuditLog.Action.APPROVE,
                object_id=first.pk,
            ).count(),
            1,
        )
        self.assertEqual(
            AuditLog.objects.filter(
                content_type="transaction",
                action=AuditLog.Action.APPROVE,
                object_id=second.pk,
            ).count(),
            1,
        )

    def test_transaction_list_shows_bulk_approve_controls_for_approver(self):
        self._create_pending(amount="100.00", description="Pending bulk UI")
        self.client.login(username=self.approver_user.username, password=self.password)

        response = self.client.get(self.transaction_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Seçilenleri onayla")
        self.assertContains(response, "transaction-bulk-approve-form")
        self.assertContains(response, 'name="transaction_ids"')

    def test_transaction_list_hides_bulk_approve_controls_for_data_entry(self):
        self._create_pending(amount="100.00")
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.transaction_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Seçilenleri onayla")
        self.assertNotContains(response, "transaction-bulk-approve-form")

    def test_htmx_bulk_approve_returns_refreshed_table(self):
        pending = self._create_pending(amount="100.00", description="HTMX bulk")
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            self.bulk_approve_url,
            data={
                "transaction_ids": [pending.pk],
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "transaction-table")
        self.assertContains(response, "badge--approved")
        self.assertNotContains(response, 'data-pending-select')
        pending.refresh_from_db()
        self.assertEqual(pending.approval_status, Transaction.ApprovalStatus.APPROVED)
