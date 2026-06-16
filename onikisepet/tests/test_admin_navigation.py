from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AdminNavigationTests(TestCase):
    password = "StrongAdminPass123!"

    def setUp(self):
        user_model = get_user_model()
        self.admin_user = user_model.objects.create_superuser(
            username="admin_navigation_user",
            email="admin-navigation@example.com",
            password=self.password,
        )

    def login_as_admin(self):
        self.client.login(
            username=self.admin_user.username,
            password=self.password,
        )

    def test_admin_index_displays_reports_link(self):
        self.login_as_admin()

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Finansal Özet")

    def test_admin_index_reports_link_points_to_report_dashboard(self):
        self.login_as_admin()
        report_dashboard_url = reverse("report_dashboard")

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{report_dashboard_url}"')
