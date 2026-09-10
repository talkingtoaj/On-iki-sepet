from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from onikisepet.models import TransactionAuditLog
from onikisepet.usecases.roles import DATA_ENTRY, TREASURER, VIEWER

from .helpers import TransactionTestMixin


class TransactionEditViewTests(TransactionTestMixin, TestCase):
    """A mistyped transaction can be corrected in place, but never silently:
    the edit requires a reason and writes an audit row per changed field.
    """

    def setUp(self):
        self.treasurer = self.create_user("edit_treasurer", group_name=TREASURER)
        self.data_entry = self.create_user("edit_data_entry", group_name=DATA_ENTRY)
        self.viewer = self.create_user("edit_viewer", group_name=VIEWER)

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
        self.other_category = self.create_category(
            name="Rent",
            category_type="expense",
        )
        self.transaction = self.create_transaction(
            transaction_type="expense",
            amount=Decimal("1500.00"),
            source_account=self.account,
            category=self.expense_category,
            description="Office supplies",
            created_by=self.treasurer,
        )
        self.url = reverse("transaction_edit", args=[self.transaction.pk])
        self.calculations = self.get_financial_calculations_module()

    def _payload(self, **overrides):
        data = {
            "date": str(self.transaction.date),
            "amount": "1050.00",
            "transaction_type": "expense",
            "payee": "",
            "account": self.account.pk,
            "category": self.expense_category.pk,
            "description": "Office supplies",
            "change_reason": "typo, receipt says 1050",
        }
        data.update(overrides)
        return data

    def _login(self, user):
        self.client.login(username=user.username, password=self.password)

    def test_treasurer_can_open_the_edit_form(self):
        self._login(self.treasurer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1500.00")

    def test_data_entry_cannot_edit_a_transaction(self):
        self._login(self.data_entry)

        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self._payload()).status_code, 403)

    def test_viewer_cannot_edit_a_transaction(self):
        self._login(self.viewer)

        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_edit_updates_the_amount(self):
        self._login(self.treasurer)

        response = self.client.post(self.url, self._payload())

        self.assertRedirects(
            response, reverse("transaction_detail", args=[self.transaction.pk])
        )
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.amount, Decimal("1050.00"))

    def test_edit_writes_an_audit_row_naming_the_old_and_new_value(self):
        self._login(self.treasurer)

        self.client.post(self.url, self._payload())

        log = TransactionAuditLog.objects.get(
            transaction=self.transaction,
            action=TransactionAuditLog.Action.CHANGED,
            field_name="amount",
        )
        self.assertEqual(log.old_value, "1500.00")
        self.assertEqual(log.new_value, "1050.00")
        self.assertEqual(log.reason, "typo, receipt says 1050")
        self.assertEqual(log.performed_by, self.treasurer)

    def test_edit_without_a_reason_is_rejected(self):
        self._login(self.treasurer)

        response = self.client.post(self.url, self._payload(change_reason=""))

        self.assertEqual(response.status_code, 200)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.amount, Decimal("1500.00"))

    def test_edit_records_one_audit_row_per_changed_field(self):
        self._login(self.treasurer)

        self.client.post(
            self.url,
            self._payload(
                category=self.other_category.pk,
                description="Rent for September",
            ),
        )

        changed = TransactionAuditLog.objects.filter(
            transaction=self.transaction,
            action=TransactionAuditLog.Action.CHANGED,
        )
        self.assertEqual(
            sorted(changed.values_list("field_name", flat=True)),
            ["amount", "category", "description"],
        )

    def test_edit_that_changes_nothing_writes_no_audit_row(self):
        self._login(self.treasurer)

        self.client.post(self.url, self._payload(amount="1500.00"))

        self.assertEqual(
            TransactionAuditLog.objects.filter(
                transaction=self.transaction,
                action=TransactionAuditLog.Action.CHANGED,
            ).count(),
            0,
        )

    def test_balance_recomputes_after_an_edit(self):
        self._login(self.treasurer)
        self.assertEqual(
            self.calculations.calculate_account_balance(self.account),
            Decimal("-500.00"),
        )

        self.client.post(self.url, self._payload())

        self.assertEqual(
            self.calculations.calculate_account_balance(self.account),
            Decimal("-50.00"),
        )

    def test_an_invalid_edit_leaves_the_transaction_untouched(self):
        self._login(self.treasurer)

        response = self.client.post(self.url, self._payload(amount="-5.00"))

        self.assertEqual(response.status_code, 200)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.amount, Decimal("1500.00"))
        self.assertEqual(TransactionAuditLog.objects.count(), 0)

    def test_a_voided_transaction_cannot_be_edited(self):
        self.transaction.is_void = True
        self.transaction.void_reason = "duplicate"
        self.transaction.voided_by = self.treasurer
        self.transaction.save()
        self._login(self.treasurer)

        response = self.client.post(self.url, self._payload())

        self.assertEqual(response.status_code, 403)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.amount, Decimal("1500.00"))

    def test_detail_page_shows_the_audit_trail(self):
        self._login(self.treasurer)
        self.client.post(self.url, self._payload())

        response = self.client.get(
            reverse("transaction_detail", args=[self.transaction.pk])
        )

        self.assertContains(response, "typo, receipt says 1050")
        self.assertContains(response, "1500.00")
        self.assertContains(response, "1050.00")

    def test_detail_page_links_to_the_edit_form_for_a_treasurer(self):
        self._login(self.treasurer)

        response = self.client.get(
            reverse("transaction_detail", args=[self.transaction.pk])
        )

        self.assertContains(response, self.url)

    def test_detail_page_hides_the_edit_link_from_data_entry(self):
        self._login(self.data_entry)

        response = self.client.get(
            reverse("transaction_detail", args=[self.transaction.pk])
        )

        self.assertNotContains(response, self.url)
