from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from onikisepet.models import AuditLog

from .helpers import TransactionTestMixin


class AuditLogTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.admin_user = self.create_user("audit_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "audit_data_entry",
            group_name="Data Entry",
        )
        self.viewer_user = self.create_user("audit_viewer", group_name="Viewer")
        self.cash = self.create_account(
            name="Audit Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.income_category = self.create_category(name="Bağış", category_type="income")
        self.transaction = self.create_transaction(
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=self.cash,
            category=self.income_category,
            created_by=self.admin_user,
        )

    def test_transaction_edit_creates_audit_log(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)
        url = reverse("transaction_edit", kwargs={"pk": self.transaction.pk})

        response = self.client.post(
            url,
            {
                "date": "2026-06-13",
                "amount": "150.00",
                "payee": "Güncel Bağışçı",
                "target_account": self.cash.pk,
                "category": self.income_category.pk,
                "description": "Güncellendi",
            },
        )

        self.assertRedirects(response, reverse("transaction_list"))
        self.assertEqual(AuditLog.objects.count(), 1)
        log = AuditLog.objects.get()
        self.assertEqual(log.action, "update")
        self.assertEqual(log.content_type, "transaction")
        self.assertEqual(log.changed_by, self.data_entry_user)
        self.assertEqual(log.after["amount"], "150.00")

    def test_viewer_cannot_edit_transaction(self):
        self.client.login(username=self.viewer_user.username, password=self.password)
        url = reverse("transaction_edit", kwargs={"pk": self.transaction.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(AuditLog.objects.count(), 0)


class TransactionAdminDeleteTests(TransactionTestMixin, TestCase):
    def setUp(self):
        from django.contrib.admin.sites import site
        from django.test import RequestFactory

        from onikisepet.admin import TransactionAdmin
        from onikisepet.models import Transaction

        self.admin_user = self.create_user("delete_admin", is_superuser=True)
        self.transaction_admin = TransactionAdmin(Transaction, site)
        self.request_factory = RequestFactory()

    def test_transaction_admin_disallows_delete(self):
        request = self.request_factory.get("/")
        request.user = self.admin_user

        self.assertFalse(self.transaction_admin.has_delete_permission(request))
