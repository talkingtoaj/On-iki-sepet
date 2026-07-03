from io import StringIO

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase

from onikisepet.models import Profile
from onikisepet.permissions import DATA_ENTRY_GROUP, VIEWER_GROUP

from .helpers import ProfileTestMixin, TransactionTestMixin


class SyncProfilesCommandTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def test_sync_profiles_creates_data_entry_profile_from_group(self):
        user = self.create_user("sync_data_entry", group_name=DATA_ENTRY_GROUP)

        call_command("sync_profiles", stdout=StringIO())

        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.role, Profile.Role.DATA_ENTRY)

    def test_sync_profiles_creates_viewer_profile_from_group(self):
        user = self.create_user("sync_viewer", group_name=VIEWER_GROUP)

        call_command("sync_profiles", stdout=StringIO())

        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.role, Profile.Role.VIEWER)

    def test_sync_profiles_prefers_data_entry_when_user_has_both_groups(self):
        user = self.create_user("sync_both_groups")
        data_entry_group, _ = Group.objects.get_or_create(name=DATA_ENTRY_GROUP)
        viewer_group, _ = Group.objects.get_or_create(name=VIEWER_GROUP)
        user.groups.add(data_entry_group, viewer_group)

        call_command("sync_profiles", stdout=StringIO())

        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.role, Profile.Role.DATA_ENTRY)

    def test_sync_profiles_updates_existing_profile_to_match_group(self):
        user = self.create_user_with_profile("sync_update", role=self.ROLE_VIEWER)
        data_entry_group, _ = Group.objects.get_or_create(name=DATA_ENTRY_GROUP)
        user.groups.add(data_entry_group)

        call_command("sync_profiles", stdout=StringIO())

        user.profile.refresh_from_db()
        self.assertEqual(user.profile.role, Profile.Role.DATA_ENTRY)

    def test_sync_profiles_skips_superuser(self):
        admin = self.create_user("sync_admin", is_superuser=True)

        call_command("sync_profiles", stdout=StringIO())

        self.assertFalse(Profile.objects.filter(user=admin).exists())

    def test_sync_profiles_does_not_create_profile_for_groupless_user(self):
        user = self.create_user("sync_groupless")

        call_command("sync_profiles", stdout=StringIO())

        self.assertFalse(Profile.objects.filter(user=user).exists())
