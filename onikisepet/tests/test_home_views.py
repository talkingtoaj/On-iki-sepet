from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse

from .helpers import ProfileTestMixin, TransactionTestMixin


class HomeViewAccessTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.home_url = reverse("home")
        self.admin_user = self.create_user("home_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "home_data_entry",
            group_name="Data Entry",
        )
        self.viewer_user = self.create_user("home_viewer", group_name="Viewer")

    def _login(self, user):
        self.client.login(username=user.username, password=self.password)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.home_url)

        login_url = resolve_url(settings.LOGIN_URL)
        self.assertRedirects(
            response,
            f"{login_url}?next={self.home_url}",
            fetch_redirect_response=False,
        )

    def test_admin_can_access_home(self):
        self._login(self.admin_user)

        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)

    def test_viewer_is_redirected_from_home_to_reports(self):
        self._login(self.viewer_user)

        response = self.client.get(self.home_url)

        self.assertRedirects(
            response,
            reverse("report_dashboard"),
            fetch_redirect_response=False,
        )

    def test_data_entry_user_can_access_home(self):
        self._login(self.data_entry_user)

        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)


class RoleBasedHomeContentTests(TransactionTestMixin, ProfileTestMixin, TestCase):
    def setUp(self):
        self.home_url = reverse("home")
        self.report_url = reverse("report_dashboard")
        self.admin_user = self.create_user("role_home_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "role_home_data_entry",
            group_name="Data Entry",
        )
        self.approver_user = self.create_data_entry_approver("role_home_approver")
        self.viewer_user = self.create_user("role_home_viewer", group_name="Viewer")

    def _login(self, user):
        self.client.login(username=user.username, password=self.password)

    def test_approver_sees_approval_panel_on_home(self):
        cash_account = self.create_account(
            name="Approver Panel Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        income_category = self.create_category(
            name="Approver Panel Income",
            category_type="income",
        )
        self.create_transaction(
            transaction_type="income",
            amount="100.00",
            target_account=cash_account,
            category=income_category,
            created_by=self.data_entry_user,
            approval_status="pending",
        )
        self._login(self.approver_user)

        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Onay Bekleyen İşler")
        self.assertContains(response, "İşlem onayı")

    def test_data_entry_without_approver_group_does_not_see_approval_panel(self):
        self._login(self.data_entry_user)

        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Onay Bekleyen İşler")

    def test_admin_sees_approval_panel_on_home(self):
        self._login(self.admin_user)

        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Onay Bekleyen İşler")

    def test_home_does_not_show_quick_actions_or_admin_panel(self):
        self._login(self.admin_user)

        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Hızlı İşlemler")
        self.assertNotContains(response, "Sistem Yönetimi")

    def test_home_does_not_show_demo_sections(self):
        self._login(self.data_entry_user)

        response = self.client.get(self.home_url)

        self.assertNotContains(response, "Etkileşimli Demo")
        self.assertNotContains(response, "HTMX Finans Rehberi")


class NavigationMenuTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.home_url = reverse("home")
        self.report_url = reverse("report_dashboard")
        self.admin_user = self.create_user("nav_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "nav_data_entry",
            group_name="Data Entry",
        )
        self.viewer_user = self.create_user("nav_viewer", group_name="Viewer")

        self.viewer_main_menu_links = {
            "Raporlar": reverse("report_dashboard"),
        }
        self.data_entry_main_menu_links = {
            "Raporlar": reverse("report_dashboard"),
            "İşlemler": reverse("transaction_list"),
            "Hesaplar": reverse("account_list"),
            "Kategoriler": reverse("category_list"),
        }
        self.transaction_create_menu_links = {
            "Nakit Gelir": reverse("cash_income_create"),
            "Nakit Gider": reverse("cash_expense_create"),
            "Banka Gideri": reverse("bank_expense_create"),
            "Online Bağış": reverse("online_donation_income_create"),
            "Transfer": reverse("transfer_create"),
            "Ekstre Yükle": reverse("import_new"),
        }
        self.setup_create_links = {
            "Kategori Oluştur": reverse("category_create"),
            "Hesap Oluştur": reverse("account_create"),
        }

    def _login(self, user):
        self.client.login(username=user.username, password=self.password)

    def _assert_contains_links(self, response, links):
        for label, url in links.items():
            with self.subTest(label=label):
                self.assertContains(response, label)
                self.assertContains(response, f'href="{url}"')

    def _assert_not_contains_links(self, response, links):
        for label, url in links.items():
            with self.subTest(label=label):
                self.assertNotContains(response, f'href="{url}"')

    def test_admin_sees_operational_menu_links(self):
        self._login(self.admin_user)

        response = self.client.get(self.home_url)

        self._assert_contains_links(response, self.data_entry_main_menu_links)

    def test_data_entry_sees_operational_menu_links(self):
        self._login(self.data_entry_user)

        response = self.client.get(self.home_url)

        self._assert_contains_links(response, self.data_entry_main_menu_links)

    def test_admin_sees_all_create_links(self):
        self._login(self.admin_user)

        response = self.client.get(self.home_url)

        self._assert_contains_links(response, self.transaction_create_menu_links)
        self._assert_contains_links(response, self.setup_create_links)

    def test_data_entry_sees_transaction_create_links_only(self):
        self._login(self.data_entry_user)

        response = self.client.get(self.home_url)

        self._assert_contains_links(response, self.transaction_create_menu_links)
        self._assert_not_contains_links(response, self.setup_create_links)

    def test_viewer_sees_only_report_menu_link(self):
        self._login(self.viewer_user)

        response = self.client.get(self.report_url)

        self._assert_contains_links(response, self.viewer_main_menu_links)
        self._assert_not_contains_links(response, {
            "İşlemler": reverse("transaction_list"),
            "Hesaplar": reverse("account_list"),
            "Kategoriler": reverse("category_list"),
        })

    def test_viewer_does_not_see_create_links(self):
        self._login(self.viewer_user)

        response = self.client.get(self.report_url)

        self._assert_not_contains_links(response, self.transaction_create_menu_links)
        self._assert_not_contains_links(response, self.setup_create_links)
