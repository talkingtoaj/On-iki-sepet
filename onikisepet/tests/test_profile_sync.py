from django.contrib.auth.models import Group
from django.test import TestCase

from onikisepet.models import Profile
from onikisepet.permissions import DATA_ENTRY_GROUP, VIEWER_GROUP
from onikisepet.usecases.profile_sync import (
    resolve_role_from_groups,
    sync_user_profile_from_groups,
)

from .helpers import ProfileTestMixin, TransactionTestMixin


class ProfileSyncUsecaseTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def test_resolve_role_from_groups_returns_data_entry_first(self):
        user = self.create_user("role_priority_user")
        data_entry_group, _ = Group.objects.get_or_create(name=DATA_ENTRY_GROUP)
        viewer_group, _ = Group.objects.get_or_create(name=VIEWER_GROUP)
        user.groups.add(data_entry_group, viewer_group)

        self.assertEqual(resolve_role_from_groups(user), Profile.Role.DATA_ENTRY)

    def test_sync_user_profile_from_groups_is_idempotent(self):
        user = self.create_user("idempotent_user", group_name=VIEWER_GROUP)

        first_profile = sync_user_profile_from_groups(user)
        second_profile = sync_user_profile_from_groups(user)

        self.assertEqual(first_profile.pk, second_profile.pk)
        self.assertEqual(Profile.objects.filter(user=user).count(), 1)
