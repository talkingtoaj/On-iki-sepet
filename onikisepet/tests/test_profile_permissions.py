from django.contrib.auth.models import Group
from django.test import TestCase

from onikisepet.models import Profile
from onikisepet.permissions import (
    APPROVER_GROUP,
    DATA_ENTRY_GROUP,
    VIEWER_GROUP,
    can_access_application,
    can_approve_transactions,
    can_create_transactions,
    can_view_operational_pages,
    can_view_transaction_list,
    can_view_reports_and_balances,
    resolve_user_role,
)

from .helpers import ProfileTestMixin, TransactionTestMixin


class ProfilePermissionTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def test_resolve_user_role_uses_profile_when_present(self):
        user = self.create_user_with_profile("profile_role_user", role=self.ROLE_DATA_ENTRY)

        self.assertEqual(resolve_user_role(user), Profile.Role.DATA_ENTRY)

    def test_resolve_user_role_falls_back_to_data_entry_group(self):
        user = self.create_user("group_data_entry_user", group_name=DATA_ENTRY_GROUP)

        self.assertEqual(resolve_user_role(user), Profile.Role.DATA_ENTRY)

    def test_resolve_user_role_falls_back_to_viewer_group(self):
        user = self.create_user("group_viewer_user", group_name=VIEWER_GROUP)

        self.assertEqual(resolve_user_role(user), Profile.Role.VIEWER)

    def test_profile_role_takes_priority_over_group(self):
        user = self.create_user_with_profile("mixed_role_user", role=self.ROLE_VIEWER)
        group, _ = Group.objects.get_or_create(name=DATA_ENTRY_GROUP)
        user.groups.add(group)

        self.assertEqual(resolve_user_role(user), Profile.Role.VIEWER)

    def test_user_without_profile_or_group_has_no_role(self):
        user = self.create_user("roleless_user")

        self.assertIsNone(resolve_user_role(user))
        self.assertFalse(can_access_application(user))

    def test_superuser_has_no_resolved_role_but_full_access(self):
        admin = self.create_user("role_admin", is_superuser=True)

        self.assertIsNone(resolve_user_role(admin))
        self.assertTrue(can_access_application(admin))
        self.assertTrue(can_create_transactions(admin))
        self.assertTrue(can_view_reports_and_balances(admin))
        self.assertTrue(can_view_operational_pages(admin))

    def test_data_entry_can_create_transactions(self):
        user = self.create_user("perm_data_entry", group_name=DATA_ENTRY_GROUP)

        self.assertTrue(can_create_transactions(user))
        self.assertTrue(can_view_operational_pages(user))
        self.assertTrue(can_view_reports_and_balances(user))

    def test_viewer_cannot_create_transactions(self):
        user = self.create_user("perm_viewer", group_name=VIEWER_GROUP)

        self.assertFalse(can_create_transactions(user))
        self.assertFalse(can_view_operational_pages(user))
        self.assertTrue(can_view_reports_and_balances(user))

    def test_data_entry_with_approver_group_can_approve_and_create(self):
        user = self.create_data_entry_approver("perm_data_entry_approver")

        self.assertTrue(can_approve_transactions(user))
        self.assertTrue(can_create_transactions(user))
        self.assertTrue(can_view_operational_pages(user))
        self.assertTrue(can_view_transaction_list(user))
        self.assertTrue(can_access_application(user))
        self.assertTrue(can_view_reports_and_balances(user))
        self.assertEqual(resolve_user_role(user), Profile.Role.DATA_ENTRY)
        self.assertTrue(user.groups.filter(name=APPROVER_GROUP).exists())

    def test_data_entry_without_approver_group_cannot_approve(self):
        user = self.create_user("perm_plain_data_entry", group_name=DATA_ENTRY_GROUP)

        self.assertFalse(can_approve_transactions(user))
        self.assertTrue(can_create_transactions(user))
