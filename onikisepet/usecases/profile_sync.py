from onikisepet.models import Profile
from onikisepet.permissions import DATA_ENTRY_GROUP, VIEWER_GROUP


def resolve_role_from_groups(user):
    if user.groups.filter(name=DATA_ENTRY_GROUP).exists():
        return Profile.Role.DATA_ENTRY
    if user.groups.filter(name=VIEWER_GROUP).exists():
        return Profile.Role.VIEWER
    return None


def sync_user_profile_from_groups(user):
    if user.is_superuser:
        return None

    role = resolve_role_from_groups(user)
    if role is None:
        return None

    profile, _created = Profile.objects.get_or_create(
        user=user,
        defaults={"role": role},
    )
    if profile.role != role:
        profile.role = role
        profile.save(update_fields=["role"])
    return profile


def sync_all_profiles_from_groups():
    from django.contrib.auth import get_user_model

    user_model = get_user_model()
    synced_profiles = []

    for user in user_model.objects.filter(is_superuser=False).iterator():
        profile = sync_user_profile_from_groups(user)
        if profile is not None:
            synced_profiles.append(profile)

    return synced_profiles
