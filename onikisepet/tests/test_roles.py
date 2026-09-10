from django.contrib.auth.models import Group, Permission
from django.test import TestCase

from onikisepet.usecases.roles import (
    DATA_ENTRY,
    ROLE_PERMISSIONS,
    TREASURER,
    VIEWER,
    seed_roles,
)


class SeedRolesTests(TestCase):
    """Permissions used to be hardcoded `is_superuser` checks in the views.
    Roles now live in Django's own permission framework so they can be granted
    per user and are visible in the admin.
    """

    def test_seed_roles_creates_the_three_groups(self):
        seed_roles()

        self.assertEqual(
            sorted(Group.objects.values_list("name", flat=True)),
            sorted([TREASURER, DATA_ENTRY, VIEWER]),
        )

    def test_each_group_gets_exactly_its_declared_permissions(self):
        seed_roles()

        for role, codenames in ROLE_PERMISSIONS.items():
            group = Group.objects.get(name=role)
            granted = set(group.permissions.values_list("codename", flat=True))
            self.assertEqual(granted, set(codenames), f"mismatch for {role}")

    def test_seed_roles_is_idempotent(self):
        seed_roles()
        seed_roles()

        self.assertEqual(Group.objects.count(), 3)
        treasurer = Group.objects.get(name=TREASURER)
        self.assertEqual(
            treasurer.permissions.count(), len(ROLE_PERMISSIONS[TREASURER])
        )

    def test_seed_roles_repairs_a_group_whose_permissions_were_changed(self):
        seed_roles()
        group = Group.objects.get(name=DATA_ENTRY)
        group.permissions.clear()

        seed_roles()

        granted = set(group.permissions.values_list("codename", flat=True))
        self.assertEqual(granted, set(ROLE_PERMISSIONS[DATA_ENTRY]))

    def test_every_declared_permission_actually_exists(self):
        """Catches a typo in a codename, which would otherwise fail silently
        and leave a role quietly missing an ability.
        """
        declared = {
            codename
            for codenames in ROLE_PERMISSIONS.values()
            for codename in codenames
        }
        existing = set(
            Permission.objects.filter(codename__in=declared).values_list(
                "codename", flat=True
            )
        )

        self.assertEqual(declared - existing, set())

    def test_data_entry_cannot_change_accounts_or_categories(self):
        self.assertNotIn("add_account", ROLE_PERMISSIONS[DATA_ENTRY])
        self.assertNotIn("change_account", ROLE_PERMISSIONS[DATA_ENTRY])
        self.assertNotIn("add_category", ROLE_PERMISSIONS[DATA_ENTRY])
        self.assertNotIn("add_exchangerate", ROLE_PERMISSIONS[DATA_ENTRY])

    def test_viewer_gets_no_write_permission_at_all(self):
        for codename in ROLE_PERMISSIONS[VIEWER]:
            self.assertTrue(
                codename.startswith("view_"),
                f"Viewer must be read-only, but has {codename}",
            )

    def test_treasurer_can_void_transactions(self):
        self.assertIn("void_transaction", ROLE_PERMISSIONS[TREASURER])

    def test_data_entry_cannot_void_transactions(self):
        self.assertNotIn("void_transaction", ROLE_PERMISSIONS[DATA_ENTRY])


class SeedRolesCommandTests(TestCase):
    def test_management_command_seeds_the_roles(self):
        from django.core.management import call_command

        call_command("seed_roles", verbosity=0)

        self.assertEqual(Group.objects.count(), 3)
