"""Tests for bilingual support.

The app is used by a Turkish congregation but maintained partly in English, so
both languages have to work and the choice has to stick. Upstream hardcoded
Turkish strings with no gettext, which made English impossible; these tests pin
the properties that stop us drifting back to a single-language app.
"""

import ast
import pathlib

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import translation

from onikisepet.models import Account, Category, Transaction
from onikisepet.usecases.roles import TREASURER

from .helpers import TransactionTestMixin

PO_PATH = (
    pathlib.Path(__file__).resolve().parent.parent.parent
    / "locale"
    / "tr"
    / "LC_MESSAGES"
    / "django.po"
)


class TurkishCatalogueTests(TestCase):
    def _entries(self):
        """(msgid, msgstr) pairs, joining the .po continuation lines."""
        text = PO_PATH.read_text(encoding="utf-8")
        entries, current, key = [], {}, None

        for line in text.splitlines():
            if line.startswith("msgid "):
                key = "msgid"
                current = {"msgid": "", "msgstr": ""}
                current["msgid"] += ast.literal_eval(line[6:].strip())
            elif line.startswith("msgstr "):
                key = "msgstr"
                current["msgstr"] += ast.literal_eval(line[7:].strip())
            elif line.startswith('"') and key:
                current[key] += ast.literal_eval(line.strip())
            elif not line.strip() and current.get("msgid"):
                entries.append((current["msgid"], current["msgstr"]))
                current, key = {}, None

        if current.get("msgid"):
            entries.append((current["msgid"], current["msgstr"]))

        return entries

    def test_catalogue_exists(self):
        self.assertTrue(
            PO_PATH.exists(),
            "The Turkish catalogue is missing. Run: manage.py makemessages -l tr",
        )

    def test_every_string_has_a_turkish_translation(self):
        """Fails loudly when a new string is added without translating it.

        Django falls back to the English msgid for an empty msgstr, so without
        this an untranslated string would quietly ship as English to Turkish
        users and nothing would go red.
        """
        untranslated = [
            msgid for msgid, msgstr in self._entries() if msgid and not msgstr
        ]

        self.assertEqual(
            untranslated,
            [],
            "Untranslated strings in locale/tr. Add translations for: "
            + ", ".join(repr(m) for m in untranslated[:10]),
        )

    def test_no_translation_accidentally_left_in_english(self):
        """Catches a msgstr pasted in unchanged from the msgid.

        A handful of words are legitimately identical in both languages, so
        those are allowed explicitly rather than by loosening the rule.
        """
        legitimately_identical = {"On İki Sepet", "Transfer"}

        copied = [
            msgid
            for msgid, msgstr in self._entries()
            if msgid
            and msgid == msgstr
            and msgid not in legitimately_identical
        ]

        self.assertEqual(copied, [], f"Untranslated copies: {copied}")


class TranslationTests(TestCase):
    def test_strings_translate_into_turkish(self):
        with translation.override("tr"):
            self.assertEqual(translation.gettext("Total Income"), "Toplam Gelir")
            self.assertEqual(translation.gettext("Receipts"), "Fişler")

    def test_strings_stay_english_under_english(self):
        with translation.override("en"):
            self.assertEqual(translation.gettext("Total Income"), "Total Income")

    def test_model_choice_labels_translate(self):
        """Choice labels render in every dropdown and report, so they matter
        as much as template text.
        """
        with translation.override("tr"):
            self.assertEqual(
                [str(label) for _, label in Transaction.TransactionType.choices],
                ["Gelir", "Gider", "Transfer"],
            )
            self.assertEqual(
                [str(label) for _, label in Category.CategoryType.choices],
                ["Gelir", "Gider"],
            )
            self.assertEqual(
                str(Account.AccountType("cash").label),
                "Nakit",
            )

    def test_validation_messages_translate(self):
        with translation.override("tr"):
            self.assertEqual(
                translation.gettext("Amount must be greater than 0."),
                "Tutar 0'dan büyük olmalıdır.",
            )


class LanguageSelectorTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("locale_user", group_name=TREASURER)
        self.client.login(username=self.user.username, password=self.password)
        self.dashboard_url = reverse("report_dashboard")

    def test_selector_offers_both_languages(self):
        response = self.client.get(self.dashboard_url)

        self.assertContains(response, 'name="language"')
        self.assertContains(response, 'value="tr"')
        self.assertContains(response, 'value="en"')

    def test_default_language_is_turkish(self):
        response = self.client.get(self.dashboard_url)

        self.assertContains(response, "Toplam Gelir")

    def test_switching_to_english_changes_the_page(self):
        self.client.post(
            reverse("set_language"),
            {"language": "en", "next": self.dashboard_url},
        )

        response = self.client.get(self.dashboard_url)

        self.assertContains(response, "Total Income")
        self.assertNotContains(response, "Toplam Gelir")

    def test_language_choice_persists_across_requests(self):
        self.client.post(
            reverse("set_language"),
            {"language": "en", "next": self.dashboard_url},
        )

        self.client.get(self.dashboard_url)
        response = self.client.get(reverse("transaction_list"))

        self.assertContains(response, "Transactions")

    def test_switching_back_to_turkish_works(self):
        self.client.post(
            reverse("set_language"),
            {"language": "en", "next": self.dashboard_url},
        )
        self.client.post(
            reverse("set_language"),
            {"language": "tr", "next": self.dashboard_url},
        )

        response = self.client.get(self.dashboard_url)

        self.assertContains(response, "Toplam Gelir")

    def test_selector_returns_the_user_to_the_page_they_were_on(self):
        target = reverse("transaction_list")

        response = self.client.post(
            reverse("set_language"), {"language": "en", "next": target}
        )

        self.assertRedirects(response, target)

    @override_settings(LANGUAGE_CODE="en")
    def test_default_language_follows_the_setting(self):
        response = self.client.get(self.dashboard_url)

        self.assertContains(response, "Total Income")

    def test_html_lang_attribute_reflects_the_active_language(self):
        response = self.client.get(self.dashboard_url)

        self.assertContains(response, 'lang="tr"')
