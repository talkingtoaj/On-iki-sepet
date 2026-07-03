from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from onikisepet.models import Transaction

from .helpers import ProfileTestMixin, TransactionTestMixin


class TransactionEditRulesTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def setUp(self):
        self.admin_user = self.create_user("edit_rules_admin", is_superuser=True)
        self.creator = self.create_user_with_profile(
            "edit_rules_creator",
            role=self.ROLE_DATA_ENTRY,
        )
        self.other_data_entry = self.create_user_with_profile(
            "edit_rules_other",
            role=self.ROLE_DATA_ENTRY,
        )
        self.viewer_user = self.create_user_with_profile(
            "edit_rules_viewer",
            role=self.ROLE_VIEWER,
        )
        self.cash_account = self.create_account(
            name="Edit Rules Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Edit Rules Income",
            category_type="income",
        )

    def _income_edit_payload(self, **overrides):
        payload = {
            "date": "2026-06-13",
            "amount": "150.00",
            "payee": "Güncel Bağışçı",
            "target_account": self.cash_account.pk,
            "category": self.income_category.pk,
            "description": "Güncellendi",
        }
        payload.update(overrides)
        return payload

    def _create_income(self, *, created_by, approval_status):
        return self.create_transaction(
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=created_by,
            approval_status=approval_status,
        )

    def test_edit_approved_transaction_returns_403_for_creator(self):
        transaction = self._create_income(
            created_by=self.creator,
            approval_status=Transaction.ApprovalStatus.APPROVED,
        )
        self.client.login(username=self.creator.username, password=self.password)
        url = reverse("transaction_edit", kwargs={"pk": transaction.pk})

        response = self.client.post(url, self._income_edit_payload())

        self.assertEqual(response.status_code, 403)
        transaction.refresh_from_db()
        self.assertEqual(transaction.amount, Decimal("100.00"))

    def test_edit_approved_transaction_returns_403_for_superuser(self):
        transaction = self._create_income(
            created_by=self.creator,
            approval_status=Transaction.ApprovalStatus.APPROVED,
        )
        self.client.login(username=self.admin_user.username, password=self.password)
        url = reverse("transaction_edit", kwargs={"pk": transaction.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)

    def test_edit_rejected_transaction_returns_403(self):
        transaction = self._create_income(
            created_by=self.creator,
            approval_status=Transaction.ApprovalStatus.REJECTED,
        )
        self.client.login(username=self.creator.username, password=self.password)
        url = reverse("transaction_edit", kwargs={"pk": transaction.pk})

        response = self.client.post(url, self._income_edit_payload())

        self.assertEqual(response.status_code, 403)

    def test_creator_can_edit_pending_transaction(self):
        transaction = self._create_income(
            created_by=self.creator,
            approval_status=Transaction.ApprovalStatus.PENDING,
        )
        self.client.login(username=self.creator.username, password=self.password)
        url = reverse("transaction_edit", kwargs={"pk": transaction.pk})

        response = self.client.post(url, self._income_edit_payload())

        self.assertRedirects(response, reverse("transaction_list"))
        transaction.refresh_from_db()
        self.assertEqual(transaction.amount, Decimal("150.00"))
        self.assertEqual(
            transaction.approval_status,
            Transaction.ApprovalStatus.PENDING,
        )

    def test_non_creator_cannot_edit_pending_transaction(self):
        transaction = self._create_income(
            created_by=self.creator,
            approval_status=Transaction.ApprovalStatus.PENDING,
        )
        self.client.login(username=self.other_data_entry.username, password=self.password)
        url = reverse("transaction_edit", kwargs={"pk": transaction.pk})

        response = self.client.post(url, self._income_edit_payload())

        self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_edit_pending_transaction(self):
        transaction = self._create_income(
            created_by=self.creator,
            approval_status=Transaction.ApprovalStatus.PENDING,
        )
        self.client.login(username=self.viewer_user.username, password=self.password)
        url = reverse("transaction_edit", kwargs={"pk": transaction.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)
