"""Password reset.

The auth views were already mounted at /auth/, but with no templates the flow
returned a server error, so in practice nobody could recover an account.
"""

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .helpers import TransactionTestMixin


@override_settings(
    LANGUAGE_CODE="en",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class PasswordResetFlowTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("reset_user")
        self.user.email = "treasurer@example.org"
        self.user.save()

    def test_reset_form_renders(self):
        response = self.client.get(reverse("password_reset"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reset password")

    def test_login_page_links_to_the_reset_form(self):
        response = self.client.get(reverse("login"))

        self.assertContains(response, reverse("password_reset"))

    def test_submitting_an_address_sends_an_email(self):
        response = self.client.post(
            reverse("password_reset"), {"email": self.user.email}
        )

        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user.email, mail.outbox[0].to)

    def test_the_email_contains_a_working_reset_link(self):
        self.client.post(reverse("password_reset"), {"email": self.user.email})
        body = mail.outbox[0].body

        link = next(
            line.strip()
            for line in body.splitlines()
            if "/auth/reset/" in line
        )
        response = self.client.get(link, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New password")

    def test_an_unknown_address_does_not_reveal_whether_it_exists(self):
        """The done page must look identical either way, or the form becomes
        a way to test which addresses hold accounts.
        """
        known = self.client.post(
            reverse("password_reset"), {"email": self.user.email}
        )
        unknown = self.client.post(
            reverse("password_reset"), {"email": "nobody@example.org"}
        )

        self.assertEqual(known.url, unknown.url)
        self.assertEqual(len(mail.outbox), 1)

    def test_the_password_can_actually_be_changed(self):
        self.client.post(reverse("password_reset"), {"email": self.user.email})
        link = next(
            line.strip()
            for line in mail.outbox[0].body.splitlines()
            if "/auth/reset/" in line
        )
        # Following the link redirects to the form at a set-password URL.
        form_url = self.client.get(link).url

        response = self.client.post(
            form_url,
            {"new_password1": "BrandNewPass456!", "new_password2": "BrandNewPass456!"},
        )

        self.assertRedirects(response, reverse("password_reset_complete"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("BrandNewPass456!"))

    def test_done_and_complete_pages_render(self):
        for name in ["password_reset_done", "password_reset_complete"]:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)

    def test_reset_pages_are_translated(self):
        """Requested via Accept-Language, because LocaleMiddleware resolves the
        language per request; a translation.override() around the client call
        would be discarded before the view runs.
        """
        response = self.client.get(
            reverse("password_reset"), headers={"accept-language": "tr"}
        )

        self.assertContains(response, "Şifre sıfırlama")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetLocalisationTests(TestCase):
    def test_email_subject_and_body_are_turkish_by_default(self):
        user = get_user_model().objects.create_user(
            username="tr_user", email="tr@example.org", password="StrongPass123!"
        )

        self.client.post(reverse("password_reset"), {"email": user.email})

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("On İki Sepet", mail.outbox[0].subject)
