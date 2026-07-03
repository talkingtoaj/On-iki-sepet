from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from onikisepet.bootstrap import bootstrap_kut, create_default_groups
from onikisepet.models import Profile, Transaction
from onikisepet.permissions import (
    APPROVER_GROUP,
    DATA_ENTRY_GROUP,
    VIEWER_GROUP,
    can_approve_transactions,
    can_create_transactions,
    can_view_operational_pages,
    can_view_transaction_list,
    user_in_approver_group,
)
from onikisepet.usecases.profile_sync import sync_user_profile_from_groups

from .helpers import ProfileTestMixin, TransactionTestMixin


class ApproverGroupSetupTests(TestCase):
    def test_create_default_groups_creates_approver_group(self):
        create_default_groups()

        self.assertTrue(Group.objects.filter(name=APPROVER_GROUP).exists())

    def test_bootstrap_kut_creates_approver_group_without_assigning_users(self):
        data_entry_user = TransactionTestMixin.create_user(
            "bootstrap_approver_group_user",
            group_name=DATA_ENTRY_GROUP,
        )

        bootstrap_kut()

        self.assertTrue(Group.objects.filter(name=APPROVER_GROUP).exists())
        self.assertFalse(
            data_entry_user.groups.filter(name=APPROVER_GROUP).exists(),
        )


class ApproverPermissionTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def test_user_in_approver_group_checks_group_membership(self):
        user = self.create_user("approver_group_member", group_name=DATA_ENTRY_GROUP)
        self.assign_user_to_group(user, APPROVER_GROUP)

        self.assertTrue(user_in_approver_group(user))

    def test_superuser_can_approve_transactions(self):
        user = self.create_user("approver_perm_admin", is_superuser=True)

        self.assertTrue(can_approve_transactions(user))

    def test_data_entry_without_approver_group_cannot_approve(self):
        user = self.create_user("plain_data_entry", group_name=DATA_ENTRY_GROUP)
        sync_user_profile_from_groups(user)

        self.assertFalse(can_approve_transactions(user))
        self.assertTrue(can_create_transactions(user))

    def test_data_entry_with_approver_group_can_approve(self):
        user = self.create_data_entry_approver("data_entry_approver")

        self.assertTrue(can_approve_transactions(user))

    def test_viewer_with_approver_group_cannot_approve(self):
        user = self.create_user("viewer_with_approver", group_name=VIEWER_GROUP)
        self.assign_user_to_group(user, APPROVER_GROUP)
        sync_user_profile_from_groups(user)

        self.assertFalse(can_approve_transactions(user))

    def test_approver_group_without_data_entry_role_cannot_approve(self):
        user = self.create_user("approver_only_group")
        self.assign_user_to_group(user, APPROVER_GROUP)

        self.assertFalse(can_approve_transactions(user))

    def test_data_entry_with_approver_group_can_create_transactions(self):
        user = self.create_data_entry_approver("data_entry_approver_create")

        self.assertTrue(can_create_transactions(user))
        self.assertTrue(can_view_operational_pages(user))
        self.assertTrue(can_view_transaction_list(user))

    def test_data_entry_with_approver_group_keeps_data_entry_profile_role(self):
        user = self.create_data_entry_approver("data_entry_approver_role")

        profile = Profile.objects.get(user=user)

        self.assertEqual(profile.role, Profile.Role.DATA_ENTRY)


class ApproverProfileRoleTests(ProfileTestMixin, TestCase):
    def test_profile_role_does_not_include_approver(self):
        role_values = {choice for choice, _ in Profile.Role.choices}

        self.assertEqual(role_values, {"viewer", "data_entry"})


class ApproverViewTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def setUp(self):
        self.approver_user = self.create_data_entry_approver("approver_view_user")
        self.data_entry_user = self.create_user(
            "approver_view_plain_data_entry",
            group_name=DATA_ENTRY_GROUP,
        )
        sync_user_profile_from_groups(self.data_entry_user)
        self.cash_account = self.create_account(
            name="Approver View Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Approver View Income",
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

    def test_data_entry_approver_can_approve_pending_transaction(self):
        self.client.login(username=self.approver_user.username, password=self.password)

        response = self.client.post(
            reverse("transaction_approve", kwargs={"pk": self.pending_transaction.pk}),
        )

        self.assertRedirects(response, reverse("transaction_list"))
        self.pending_transaction.refresh_from_db()
        self.assertEqual(
            self.pending_transaction.approval_status,
            Transaction.ApprovalStatus.APPROVED,
        )

    def test_data_entry_approver_can_reject_pending_transaction_with_reason(self):
        self.client.login(username=self.approver_user.username, password=self.password)

        response = self.client.post(
            reverse("transaction_reject", kwargs={"pk": self.pending_transaction.pk}),
            data={"rejection_reason": "Kategori yanlış"},
        )

        self.assertRedirects(response, reverse("transaction_list"))
        self.pending_transaction.refresh_from_db()
        self.assertEqual(
            self.pending_transaction.approval_status,
            Transaction.ApprovalStatus.REJECTED,
        )
        self.assertEqual(self.pending_transaction.rejection_reason, "Kategori yanlış")

    def test_data_entry_approver_can_create_cash_income(self):
        self.client.login(username=self.approver_user.username, password=self.password)

        response = self.client.get(reverse("cash_income_create"))

        self.assertEqual(response.status_code, 200)

    def test_plain_data_entry_cannot_approve_pending_transaction(self):
        self.client.login(
            username=self.data_entry_user.username,
            password=self.password,
        )

        response = self.client.post(
            reverse("transaction_approve", kwargs={"pk": self.pending_transaction.pk}),
        )

        self.assertEqual(response.status_code, 403)
        self.pending_transaction.refresh_from_db()
        self.assertEqual(
            self.pending_transaction.approval_status,
            Transaction.ApprovalStatus.PENDING,
        )


class ApproverProfileSyncTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def test_sync_profiles_preserves_approver_group_membership(self):
        user = self.create_user("sync_approver_membership", group_name=DATA_ENTRY_GROUP)
        self.assign_user_to_group(user, APPROVER_GROUP)

        call_command("sync_profiles")

        self.assertTrue(user.groups.filter(name=APPROVER_GROUP).exists())
        self.assertEqual(
            Profile.objects.get(user=user).role,
            Profile.Role.DATA_ENTRY,
        )
