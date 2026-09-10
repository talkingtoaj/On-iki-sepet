# These tests assert the English wording of the interface. The app now
# defaults to Turkish, so the language is pinned here rather than left
# implicit; Turkish rendering is covered in test_localization.py.
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from onikisepet.models import TransactionAuditLog
from onikisepet.usecases.roles import DATA_ENTRY, TREASURER, VIEWER

from .helpers import TransactionTestMixin


@override_settings(LANGUAGE_CODE="en")
class TransactionVoidViewTests(TransactionTestMixin, TestCase):
    """Void replaces delete. The row survives for the audit trail, leaves every
    report, and records who voided it and why.
    """

    def setUp(self):
        self.treasurer = self.create_user("void_treasurer", group_name=TREASURER)
        self.data_entry = self.create_user("void_data_entry", group_name=DATA_ENTRY)
        self.viewer = self.create_user("void_viewer", group_name=VIEWER)

        self.account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
            opening_balance=Decimal("1000.00"),
        )
        self.expense_category = self.create_category(
            name="Supplies",
            category_type="expense",
        )
        self.transaction = self.create_transaction(
            transaction_type="expense",
            amount=Decimal("200.00"),
            source_account=self.account,
            category=self.expense_category,
            created_by=self.treasurer,
        )
        self.url = reverse("transaction_void", args=[self.transaction.pk])
        self.detail_url = reverse(
            "transaction_detail", args=[self.transaction.pk]
        )
        self.calculations = self.get_financial_calculations_module()

    def _login(self, user):
        self.client.login(username=user.username, password=self.password)

    def test_treasurer_can_open_the_void_confirmation(self):
        self._login(self.treasurer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Void")

    def test_data_entry_cannot_void(self):
        self._login(self.data_entry)

        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(
            self.client.post(self.url, {"void_reason": "nope"}).status_code, 403
        )

    def test_viewer_cannot_void(self):
        self._login(self.viewer)

        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_voiding_marks_the_transaction_and_records_who_and_why(self):
        self._login(self.treasurer)

        response = self.client.post(self.url, {"void_reason": "entered twice"})

        self.assertRedirects(response, self.detail_url)
        self.transaction.refresh_from_db()
        self.assertTrue(self.transaction.is_void)
        self.assertEqual(self.transaction.void_reason, "entered twice")
        self.assertEqual(self.transaction.voided_by, self.treasurer)
        self.assertIsNotNone(self.transaction.voided_at)

    def test_voiding_writes_an_audit_row(self):
        self._login(self.treasurer)

        self.client.post(self.url, {"void_reason": "entered twice"})

        log = TransactionAuditLog.objects.get(
            transaction=self.transaction,
            action=TransactionAuditLog.Action.VOIDED,
        )
        self.assertEqual(log.reason, "entered twice")
        self.assertEqual(log.performed_by, self.treasurer)

    def test_voiding_without_a_reason_is_rejected(self):
        self._login(self.treasurer)

        response = self.client.post(self.url, {"void_reason": ""})

        self.assertEqual(response.status_code, 200)
        self.transaction.refresh_from_db()
        self.assertFalse(self.transaction.is_void)

    def test_voiding_removes_the_transaction_from_the_balance(self):
        self._login(self.treasurer)
        self.assertEqual(
            self.calculations.calculate_account_balance(self.account),
            Decimal("800.00"),
        )

        self.client.post(self.url, {"void_reason": "entered twice"})

        self.assertEqual(
            self.calculations.calculate_account_balance(self.account),
            Decimal("1000.00"),
        )

    def test_the_transaction_row_is_not_deleted(self):
        self._login(self.treasurer)

        self.client.post(self.url, {"void_reason": "entered twice"})

        self.assertEqual(self.get_transaction_model().objects.count(), 1)

    def test_an_already_voided_transaction_cannot_be_voided_again(self):
        self._login(self.treasurer)
        self.client.post(self.url, {"void_reason": "entered twice"})

        response = self.client.post(self.url, {"void_reason": "again"})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            TransactionAuditLog.objects.filter(
                action=TransactionAuditLog.Action.VOIDED
            ).count(),
            1,
        )

    def test_detail_page_marks_a_voided_transaction(self):
        self._login(self.treasurer)
        self.client.post(self.url, {"void_reason": "entered twice"})

        response = self.client.get(self.detail_url)

        self.assertContains(response, "VOIDED")
        self.assertContains(response, "entered twice")

    def test_transaction_list_marks_a_voided_transaction(self):
        self._login(self.treasurer)
        self.client.post(self.url, {"void_reason": "entered twice"})

        response = self.client.get(reverse("transaction_list"))

        self.assertContains(response, "VOIDED")

    def test_detail_page_hides_the_void_link_once_voided(self):
        self._login(self.treasurer)
        self.client.post(self.url, {"void_reason": "entered twice"})

        response = self.client.get(self.detail_url)

        self.assertNotContains(response, self.url)
