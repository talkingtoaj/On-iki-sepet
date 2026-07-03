from django.contrib.auth.models import Group

from onikisepet.kut_accounts import load_kut_accounts
from onikisepet.kut_categories import load_kut_categories
from onikisepet.permissions import APPROVER_GROUP, DATA_ENTRY_GROUP, VIEWER_GROUP
from onikisepet.usecases.profile_sync import sync_all_profiles_from_groups

DEFAULT_GROUPS = (DATA_ENTRY_GROUP, VIEWER_GROUP, APPROVER_GROUP)


def create_default_groups():
    created_count = 0

    for name in DEFAULT_GROUPS:
        _group, created = Group.objects.get_or_create(name=name)
        if created:
            created_count += 1

    return created_count


def bootstrap_kut():
    groups_created = create_default_groups()
    synced_profiles = sync_all_profiles_from_groups()
    accounts_created = load_kut_accounts()
    categories_created = load_kut_categories()

    return {
        "groups_created": groups_created,
        "profiles_synced": len(synced_profiles),
        "accounts_created": accounts_created,
        "categories_created": categories_created,
    }
