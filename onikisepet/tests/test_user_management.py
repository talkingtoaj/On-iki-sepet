from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from onikisepet.models import Profile
from onikisepet.permissions import DATA_ENTRY_GROUP, VIEWER_GROUP

from .helpers import ProfileTestMixin, TransactionTestMixin


class PasswordResetFlowTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.login_url = reverse("login")
        self.password_reset_url = reverse("password_reset")
        self.user = self.create_user("reset_user")

    def test_login_page_links_to_password_reset(self):
        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("password_reset"))

    def test_password_reset_page_is_accessible_for_anonymous_users(self):
        response = self.client.get(self.password_reset_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Şifre sıfırlama")

    def test_password_reset_sends_email_for_known_user(self):
        response = self.client.post(
            self.password_reset_url,
            data={"email": self.user.email},
        )

        self.assertRedirects(
            response,
            reverse("password_reset_done"),
            fetch_redirect_response=False,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user.email, mail.outbox[0].to)

    def test_password_reset_confirm_sets_new_password(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        confirm_url = reverse(
            "password_reset_confirm",
            kwargs={"uidb64": uid, "token": token},
        )
        new_password = "NewSecurePass456!"

        response = self.client.get(confirm_url)
        set_password_url = response["Location"]
        response = self.client.post(
            set_password_url,
            data={
                "new_password1": new_password,
                "new_password2": new_password,
            },
        )

        self.assertRedirects(
            response,
            reverse("password_reset_complete"),
            fetch_redirect_response=False,
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))


class UserManagementViewTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def setUp(self):
        self.list_url = reverse("user_list")
        self.create_url = reverse("user_create")
        self.superuser = self.create_user("user_mgmt_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "user_mgmt_data_entry",
            group_name=DATA_ENTRY_GROUP,
        )

    def _login_superuser(self):
        self.client.login(username=self.superuser.username, password=self.password)

    def test_superuser_can_access_user_list(self):
        self._login_superuser()

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.data_entry_user.username)

    def test_non_superuser_cannot_access_user_management(self):
        self.client.login(
            username=self.data_entry_user.username,
            password=self.password,
        )

        for url in (self.list_url, self.create_url):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

    def test_superuser_can_create_user_with_data_entry_group(self):
        self._login_superuser()

        response = self.client.post(
            self.create_url,
            data={
                "username": "new_finance_user",
                "email": "new_finance@example.com",
                "password1": "CreateUserPass789!",
                "password2": "CreateUserPass789!",
                "groups": [self._group_id(DATA_ENTRY_GROUP)],
            },
        )

        self.assertRedirects(response, self.list_url, fetch_redirect_response=False)
        user = get_user_model().objects.get(username="new_finance_user")
        self.assertTrue(user.groups.filter(name=DATA_ENTRY_GROUP).exists())
        self.assertEqual(user.profile.role, Profile.Role.DATA_ENTRY)

    def test_superuser_can_assign_groups_to_existing_user(self):
        roleless_user = self.create_user("assign_groups_user")
        edit_url = reverse("user_edit", kwargs={"pk": roleless_user.pk})
        self._login_superuser()

        response = self.client.post(
            edit_url,
            data={
                "username": roleless_user.username,
                "email": roleless_user.email,
                "groups": [self._group_id(VIEWER_GROUP)],
            },
        )

        self.assertRedirects(response, self.list_url, fetch_redirect_response=False)
        roleless_user.refresh_from_db()
        self.assertTrue(roleless_user.groups.filter(name=VIEWER_GROUP).exists())
        self.assertEqual(roleless_user.profile.role, Profile.Role.VIEWER)

    def test_superuser_can_reset_user_password(self):
        target_user = self.create_user("password_reset_target")
        edit_url = reverse("user_edit", kwargs={"pk": target_user.pk})
        new_password = "AdminResetPass321!"
        self._login_superuser()

        response = self.client.post(
            edit_url,
            data={
                "username": target_user.username,
                "email": target_user.email,
                "password_reset_enabled": "1",
                "new_password1": new_password,
                "new_password2": new_password,
            },
        )

        self.assertRedirects(response, self.list_url, fetch_redirect_response=False)
        target_user.refresh_from_db()
        self.assertTrue(target_user.check_password(new_password))

    def test_user_edit_get_hides_password_fields(self):
        target_user = self.create_user("hidden_password_user")
        edit_url = reverse("user_edit", kwargs={"pk": target_user.pk})
        self._login_superuser()

        response = self.client.get(edit_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Şifreyi yenile")
        self.assertContains(response, 'id="toggle-password-reset"')
        self.assertContains(response, 'id="password-reset-panel"')
        content = response.content.decode()
        panel_index = content.index('id="password-reset-panel"')
        panel_snippet = content[panel_index : panel_index + 160]
        self.assertIn("hidden", panel_snippet)
        self.assertNotIn('id="toggle-password-reset" hidden', content)
        self.assertContains(response, 'id="password-reset-fields-template"')

    def test_user_edit_ignores_password_when_reset_not_enabled(self):
        target_user = self.create_user("autofill_sim_user")
        edit_url = reverse("user_edit", kwargs={"pk": target_user.pk})
        self._login_superuser()

        response = self.client.post(
            edit_url,
            data={
                "username": target_user.username,
                "email": target_user.email,
                "password_reset_enabled": "0",
                "new_password1": "ShouldBeIgnored111!",
                "new_password2": "ShouldBeIgnored111!",
            },
        )

        self.assertRedirects(response, self.list_url, fetch_redirect_response=False)
        target_user.refresh_from_db()
        self.assertTrue(target_user.check_password(self.password))

    def test_user_edit_post_with_password_validation_error_keeps_form(self):
        target_user = self.create_user("password_mismatch_user")
        edit_url = reverse("user_edit", kwargs={"pk": target_user.pk})
        self._login_superuser()

        response = self.client.post(
            edit_url,
            data={
                "username": target_user.username,
                "email": target_user.email,
                "password_reset_enabled": "1",
                "new_password1": "MismatchPass111!",
                "new_password2": "MismatchPass222!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "eşleşmiyor")
        self.assertContains(response, 'name="new_password1"')
        self.assertContains(response, 'name="new_password2"')
        target_user.refresh_from_db()
        self.assertTrue(target_user.check_password(self.password))

    def _group_id(self, group_name):
        from django.contrib.auth.models import Group

        group, _ = Group.objects.get_or_create(name=group_name)
        return group.pk


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PendingAccessOnboardingTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.home_url = reverse("home")
        self.pending_url = reverse("pending_access")
        self.roleless_user = self.create_user("pending_user")

    def test_roleless_user_is_redirected_to_pending_access_not_403(self):
        self.client.login(username=self.roleless_user.username, password=self.password)

        response = self.client.get(self.home_url)

        self.assertRedirects(
            response,
            self.pending_url,
            fetch_redirect_response=False,
        )

    def test_roleless_user_can_view_pending_access_page(self):
        self.client.login(username=self.roleless_user.username, password=self.password)

        response = self.client.get(self.pending_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "henüz atanmadı")

    def test_user_with_group_is_not_redirected_to_pending_access(self):
        user = self.create_user("assigned_user", group_name=DATA_ENTRY_GROUP)
        self.client.login(username=user.username, password=self.password)

        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)
