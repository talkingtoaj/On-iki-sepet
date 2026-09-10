"""Role definitions for the church finance app.

Roles are Django `Group`s carrying real model permissions, rather than
hardcoded `is_superuser` checks inside views. That way the treasurer can grant
a role from the admin, and the same permission governs both the app and the
Django admin.

The books include donor records, so reading is itself a granted permission: an
account with no role sees nothing. Writing splits further, because posting a
transaction is routine work while changing accounts, categories or exchange
rates alters every reported figure.
"""

from django.contrib.auth.models import Group, Permission

TREASURER = "Treasurer"
DATA_ENTRY = "Data Entry"
VIEWER = "Viewer"

READ_ONLY_PERMISSIONS = [
    "view_category",
    "view_account",
    "view_exchangerate",
    "view_transaction",
    "view_receipt",
]

DATA_ENTRY_PERMISSIONS = READ_ONLY_PERMISSIONS + [
    "add_transaction",
    "add_receipt",
]

TREASURER_PERMISSIONS = DATA_ENTRY_PERMISSIONS + [
    "add_category",
    "change_category",
    "add_account",
    "change_account",
    "add_exchangerate",
    "change_exchangerate",
    "change_transaction",
    "void_transaction",
]

ROLE_PERMISSIONS = {
    TREASURER: TREASURER_PERMISSIONS,
    DATA_ENTRY: DATA_ENTRY_PERMISSIONS,
    VIEWER: READ_ONLY_PERMISSIONS,
}


def seed_roles():
    """Create the role groups and set their permissions to match the
    declarations above. Safe to run repeatedly; it also repairs a group whose
    permissions were changed by hand.
    """
    groups = {}

    for role, codenames in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=role)
        permissions = Permission.objects.filter(
            codename__in=codenames,
            content_type__app_label="onikisepet",
        )
        group.permissions.set(permissions)
        groups[role] = group

    return groups
