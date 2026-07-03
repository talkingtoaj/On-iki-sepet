from django.contrib.auth import get_user_model
from django.test import TestCase

from onikisepet.models import Profile

from .helpers import ProfileTestMixin


class ProfileModelTests(ProfileTestMixin, TestCase):
    def test_profile_model_exists(self):
        self.assertEqual(self.get_profile_model().__name__, "Profile")

    def test_profile_has_viewer_and_data_entry_roles(self):
        role_values = {choice for choice, _ in Profile.Role.choices}

        self.assertEqual(role_values, {"viewer", "data_entry"})

    def test_profile_can_be_created_for_user(self):
        user = get_user_model().objects.create_user(
            username="profile_user",
            password="StrongTestPass123!",
        )

        profile = self.create_profile(user, role=self.ROLE_DATA_ENTRY)

        self.assertEqual(profile.user, user)
        self.assertEqual(profile.role, Profile.Role.DATA_ENTRY)

    def test_profile_str_includes_username_and_role(self):
        user = self.create_user_with_profile("profile_str_user", role=self.ROLE_VIEWER)

        profile = user.profile
        value = str(profile)

        self.assertIn("profile_str_user", value)
        self.assertIn("Viewer", value)
