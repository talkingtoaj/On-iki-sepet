from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from onikisepet.models import Transaction, TransactionAuditLog

from .helpers import TransactionTestMixin


@override_settings(LANGUAGE_CODE="en")
class TransactionAuditLogModelTests(TransactionTestMixin, TestCase):
    """The audit trail is the point of a church finance system: nothing may
    change without a durable record of who changed it and why. Audit rows are
    therefore append-only, and a transaction carrying them cannot be deleted.
    """

    def setUp(self):
        self.user = self.create_user("audit_user", is_superuser=True)
        self.account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.category = self.create_category(name="Supplies", category_type="expense")
        self.transaction = self.create_transaction(
            transaction_type="expense",
            amount=Decimal("100.00"),
            source_account=self.account,
            category=self.category,
            created_by=self.user,
        )

    def _log(self, **overrides):
        data = {
            "transaction": self.transaction,
            "action": TransactionAuditLog.Action.CHANGED,
            "field_name": "amount",
            "old_value": "100.00",
            "new_value": "50.00",
            "reason": "typo, receipt says 50",
            "performed_by": self.user,
        }
        data.update(overrides)
        return TransactionAuditLog.objects.create(**data)

    def test_audit_row_stores_who_what_and_why(self):
        log = self._log()
        log.refresh_from_db()

        self.assertEqual(log.transaction, self.transaction)
        self.assertEqual(log.field_name, "amount")
        self.assertEqual(log.old_value, "100.00")
        self.assertEqual(log.new_value, "50.00")
        self.assertEqual(log.reason, "typo, receipt says 50")
        self.assertEqual(log.performed_by, self.user)
        self.assertIsNotNone(log.created_at)

    def test_audit_row_cannot_be_edited(self):
        log = self._log()

        log.new_value = "999.00"

        with self.assertRaises(ValidationError):
            log.save()

    def test_audit_row_cannot_be_deleted(self):
        log = self._log()

        with self.assertRaises(ValidationError):
            log.delete()

    def test_audit_rows_cannot_be_bulk_deleted(self):
        self._log()

        with self.assertRaises(ValidationError):
            TransactionAuditLog.objects.all().delete()

    def test_a_transaction_with_audit_history_cannot_be_deleted(self):
        """Deletion is replaced by voiding, so the record always survives."""
        from django.db.models import ProtectedError

        self._log()

        with self.assertRaises(ProtectedError):
            self.transaction.delete()

    def test_audit_rows_are_ordered_oldest_first(self):
        first = self._log(field_name="amount")
        second = self._log(field_name="payee")

        history = list(self.transaction.audit_logs.all())

        self.assertEqual(history, [first, second])

    def test_str_describes_the_change(self):
        log = self._log()

        self.assertIn("amount", str(log))
        self.assertIn(self.user.get_username(), str(log))


@override_settings(LANGUAGE_CODE="en")
class TransactionVoidingTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("void_model_user", is_superuser=True)
        self.account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.category = self.create_category(name="Supplies", category_type="expense")
        self.transaction = self.create_transaction(
            transaction_type="expense",
            amount=Decimal("100.00"),
            source_account=self.account,
            category=self.category,
            created_by=self.user,
        )

    def test_a_new_transaction_is_not_void(self):
        self.assertFalse(self.transaction.is_void)

    def test_voiding_requires_a_reason(self):
        self.transaction.is_void = True

        with self.assertRaises(ValidationError):
            self.transaction.save()

    def test_voiding_with_a_reason_is_allowed(self):
        self.transaction.is_void = True
        self.transaction.void_reason = "duplicate entry"
        self.transaction.voided_by = self.user
        self.transaction.save()

        self.transaction.refresh_from_db()
        self.assertTrue(self.transaction.is_void)
        self.assertEqual(self.transaction.void_reason, "duplicate entry")
        self.assertIsNotNone(self.transaction.voided_at)

    def test_active_queryset_excludes_voided_transactions(self):
        self.transaction.is_void = True
        self.transaction.void_reason = "duplicate entry"
        self.transaction.voided_by = self.user
        self.transaction.save()

        self.assertEqual(Transaction.objects.active().count(), 0)
        self.assertEqual(Transaction.objects.voided().count(), 1)
        self.assertEqual(Transaction.objects.count(), 1)
