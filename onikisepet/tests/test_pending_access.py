"""Signed-in users who have no role yet.

Reading the books is a granted permission, so a new account starts with access
to nothing. Previously that produced a bare 403, which reads as a fault rather
than as "an administrator has not given you a role yet".
"""

from django.test import TestCase, override_settings
from django.urls import reverse

from onikisepet.usecases.roles import TREASURER, VIEWER

from .helpers import TransactionTestMixin


@override_settings(LANGUAGE_CODE="en")
class PendingAccessTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.no_role = self.create_user("no_role_user")
        self.viewer = self.create_user("viewer_user", group_name=VIEWER)
        self.treasurer = self.create_user("treasurer_user", group_name=TREASURER)
        self.url = reverse("report_dashboard")

    def _get_as(self, user):
        self.client.login(username=user.username, password=self.password)
        return self.client.get(self.url)

    def test_role_less_user_sees_an_explanation(self):
        response = self._get_as(self.no_role)

        self.assertContains(response, "Waiting for access", status_code=403)
        self.assertContains(response, "administrator", status_code=403)

    def test_role_less_user_still_gets_a_403_status(self):
        """The page explains the situation but must not pretend access was
        granted, so the status code stays 403.
        """
        response = self._get_as(self.no_role)

        self.assertEqual(response.status_code, 403)

    def test_role_less_user_is_told_who_they_signed_in_as(self):
        response = self._get_as(self.no_role)

        self.assertContains(response, "no_role_user", status_code=403)

    def test_a_user_with_a_role_is_unaffected(self):
        response = self._get_as(self.viewer)

        self.assertEqual(response.status_code, 200)

    def test_a_roled_user_denied_a_specific_action_does_not_see_pending_access(self):
        """A viewer refused the account form has a role; they must get a plain
        refusal, not the "waiting for access" message.
        """
        self.client.login(username=self.viewer.username, password=self.password)

        response = self.client.get(reverse("account_create"))

        self.assertEqual(response.status_code, 403)
        self.assertNotContains(response, "Waiting for access", status_code=403)

    def test_superuser_is_unaffected(self):
        admin = self.create_user("admin_user", is_superuser=True)

        response = self._get_as(admin)

        self.assertEqual(response.status_code, 200)

    def test_pending_page_offers_a_way_to_sign_out(self):
        response = self._get_as(self.no_role)

        self.assertContains(response, reverse("logout"), status_code=403)
