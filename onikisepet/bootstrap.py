from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from onikisepet.kut_accounts import load_kut_accounts
from onikisepet.kut_categories import load_kut_categories
from onikisepet.permissions import APPROVER_GROUP, DATA_ENTRY_GROUP, VIEWER_GROUP
from onikisepet.usecases.profile_sync import sync_all_profiles_from_groups

DEFAULT_GROUPS = (DATA_ENTRY_GROUP, VIEWER_GROUP, APPROVER_GROUP)
DEFAULT_SUPERUSER_USERNAME = "admin"
DEFAULT_SUPERUSER_PASSWORD = "qweqweqwe"
DEFAULT_SUPERUSER_EMAIL = "admin@example.com"


def create_default_groups():
    created_count = 0

    for name in DEFAULT_GROUPS:
        _group, created = Group.objects.get_or_create(name=name)
        if created:
            created_count += 1

    return created_count


def create_default_superuser():
    user_model = get_user_model()
    if user_model.objects.filter(username=DEFAULT_SUPERUSER_USERNAME).exists():
        return 0

    user_model.objects.create_superuser(
        username=DEFAULT_SUPERUSER_USERNAME,
        email=DEFAULT_SUPERUSER_EMAIL,
        password=DEFAULT_SUPERUSER_PASSWORD,
    )
    return 1


def bootstrap_kut():
    groups_created = create_default_groups()
    superuser_created = create_default_superuser()
    synced_profiles = sync_all_profiles_from_groups()
    accounts_created = load_kut_accounts()
    categories_created = load_kut_categories()

    return {
        "groups_created": groups_created,
        "superuser_created": superuser_created,
        "profiles_synced": len(synced_profiles),
        "accounts_created": accounts_created,
        "categories_created": categories_created,
    }
