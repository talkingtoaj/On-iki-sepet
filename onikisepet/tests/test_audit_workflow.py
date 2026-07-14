from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from onikisepet.models import AuditLog, Transaction

from .helpers import ProfileTestMixin, TransactionTestMixin


class AuditWorkflowTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def setUp(self):
        self.admin_user = self.create_user("audit_workflow_admin", is_superuser=True)
        self.data_entry_user = self.create_user_with_profile(
            "audit_workflow_data_entry",
            role=self.ROLE_DATA_ENTRY,
        )
        self.cash_account = self.create_account(
            name="Audit Workflow Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Audit Workflow Income",
            category_type="income",
        )

    def test_audit_log_action_includes_approve_and_reject(self):
        actions = {choice for choice, _ in AuditLog.Action.choices}
        self.assertIn("approve", actions)
        self.assertIn("reject", actions)
        self.assertIn("resubmit", actions)

    def test_transaction_create_logs_audit_entry(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        self.client.post(
            reverse("cash_income_create"),
            data={
                "date": "2026-06-15",
                "donor_name": "Bağışçı",
                "amount": "250.00",
                "cash_account": self.cash_account.pk,
                "category": self.income_category.pk,
                "description": "",
            },
        )

        transaction = Transaction.objects.get()
        log = AuditLog.objects.get(
            content_type="transaction",
            object_id=transaction.pk,
            action=AuditLog.Action.CREATE,
        )
        self.assertEqual(log.changed_by, self.data_entry_user)

    def test_transaction_approve_logs_audit_entry(self):
        transaction = self.create_transaction(
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.data_entry_user,
            approval_status=Transaction.ApprovalStatus.PENDING,
        )
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(
            reverse("transaction_approve", kwargs={"pk": transaction.pk}),
        )

        log = AuditLog.objects.get(
            content_type="transaction",
            object_id=transaction.pk,
            action=AuditLog.Action.APPROVE,
        )
        self.assertEqual(log.changed_by, self.admin_user)
        self.assertEqual(log.after["approval_status"], Transaction.ApprovalStatus.APPROVED)

    def test_transaction_reject_logs_audit_entry_with_reason(self):
        transaction = self.create_transaction(
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.data_entry_user,
            approval_status=Transaction.ApprovalStatus.PENDING,
        )
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(
            reverse("transaction_reject", kwargs={"pk": transaction.pk}),
            data={"rejection_reason": "Tutar hatalı"},
        )

        log = AuditLog.objects.get(
            content_type="transaction",
            object_id=transaction.pk,
            action=AuditLog.Action.REJECT,
        )
        self.assertEqual(log.changed_by, self.admin_user)
        self.assertEqual(log.after["rejection_reason"], "Tutar hatalı")

    def test_pending_transaction_edit_logs_update_audit(self):
        transaction = self.create_transaction(
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.data_entry_user,
            approval_status=Transaction.ApprovalStatus.PENDING,
        )
        self.client.login(username=self.data_entry_user.username, password=self.password)

        self.client.post(
            reverse("transaction_edit", kwargs={"pk": transaction.pk}),
            data={
                "date": "2026-06-13",
                "amount": "150.00",
                "payee": "Güncel Bağışçı",
                "target_account": self.cash_account.pk,
                "category": self.income_category.pk,
                "description": "Güncellendi",
            },
        )

        log = AuditLog.objects.get(
            content_type="transaction",
            object_id=transaction.pk,
            action=AuditLog.Action.UPDATE,
        )
        self.assertEqual(log.changed_by, self.data_entry_user)
        self.assertEqual(log.after["amount"], "150.00")

    def test_rejected_transaction_resubmit_logs_resubmit_audit(self):
        transaction = self.create_transaction(
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.data_entry_user,
            approval_status=Transaction.ApprovalStatus.REJECTED,
        )
        transaction.rejection_reason = "Tutar hatalı"
        transaction.save(update_fields=["rejection_reason", "updated_at"])
        self.client.login(username=self.data_entry_user.username, password=self.password)

        self.client.post(
            reverse("transaction_edit", kwargs={"pk": transaction.pk}),
            data={
                "date": "2026-06-13",
                "amount": "150.00",
                "payee": "Güncel Bağışçı",
                "target_account": self.cash_account.pk,
                "category": self.income_category.pk,
                "description": "Güncellendi",
            },
        )

        log = AuditLog.objects.get(
            content_type="transaction",
            object_id=transaction.pk,
            action=AuditLog.Action.RESUBMIT,
        )
        self.assertEqual(log.changed_by, self.data_entry_user)
        self.assertEqual(log.before["rejection_reason"], "Tutar hatalı")
        self.assertEqual(log.after["approval_status"], Transaction.ApprovalStatus.PENDING)
        self.assertEqual(log.after["rejection_reason"], "")
