"""The container health endpoint.

Cloud Run uses this to decide whether a revision can take traffic, so it has
to fail when the database is unreachable rather than merely proving that
Python started.
"""

from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(LANGUAGE_CODE="en")
class HealthCheckTests(TestCase):
    def setUp(self):
        self.url = reverse("health_check")

    def test_reports_ok_when_the_database_answers(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": True})

    def test_reports_unavailable_when_the_database_is_unreachable(self):
        """A revision that cannot reach Cloud SQL must not be marked healthy."""
        with patch(
            "config.health.connection.ensure_connection",
            side_effect=OSError("no route to host"),
        ):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "unavailable")

    def test_needs_no_authentication(self):
        """The platform's checker cannot sign in."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_rejects_non_get_methods(self):
        self.assertEqual(self.client.post(self.url).status_code, 405)
