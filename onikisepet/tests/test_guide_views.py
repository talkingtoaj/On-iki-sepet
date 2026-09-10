"""Guide pages.

The people entering transactions are volunteers rather than bookkeepers, and
the commonest error is picking the wrong record kind — a transfer entered as
income overstates the church's income.
"""

from django.test import TestCase, override_settings
from django.urls import reverse

from onikisepet.usecases.roles import DATA_ENTRY, VIEWER

from .helpers import TransactionTestMixin


@override_settings(LANGUAGE_CODE="en")
class GuideViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.data_entry = self.create_user("guide_entry", group_name=DATA_ENTRY)
        self.viewer = self.create_user("guide_viewer", group_name=VIEWER)
        self.no_role = self.create_user("guide_no_role")

    def _get(self, user, name):
        self.client.login(username=user.username, password=self.password)
        return self.client.get(reverse(name))

    def test_record_type_guide_renders_for_data_entry(self):
        response = self._get(self.data_entry, "record_type_guide")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Which record should I use?")

    def test_record_type_guide_covers_all_three_kinds(self):
        response = self._get(self.data_entry, "record_type_guide")

        self.assertContains(response, "Income")
        self.assertContains(response, "Expense")
        self.assertContains(response, "Transfer")

    def test_record_type_guide_explains_that_transfers_are_neither(self):
        """The single most consequential rule for a volunteer to understand."""
        response = self._get(self.data_entry, "record_type_guide")

        self.assertContains(response, "never income and never an expense")

    def test_finance_guide_renders(self):
        response = self._get(self.viewer, "finance_guide")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "How the books work")

    def test_finance_guide_explains_currency_handling(self):
        response = self._get(self.viewer, "finance_guide")

        self.assertContains(response, "never added together")
        self.assertContains(response, "incomplete")

    def test_finance_guide_names_the_base_currency(self):
        response = self._get(self.viewer, "finance_guide")

        self.assertContains(response, "TRY")

    def test_finance_guide_explains_that_nothing_is_deleted(self):
        response = self._get(self.viewer, "finance_guide")

        self.assertContains(response, "Nothing is ever deleted")

    def test_guides_are_cross_linked(self):
        records = self._get(self.viewer, "record_type_guide")
        finance = self._get(self.viewer, "finance_guide")

        self.assertContains(records, reverse("finance_guide"))
        self.assertContains(finance, reverse("record_type_guide"))

    def test_guide_is_linked_from_the_navigation(self):
        response = self._get(self.viewer, "report_dashboard")

        self.assertContains(response, reverse("finance_guide"))

    def test_role_less_user_cannot_reach_the_guides(self):
        for name in ["finance_guide", "record_type_guide"]:
            self.assertEqual(self._get(self.no_role, name).status_code, 403)

    def test_anonymous_user_is_redirected(self):
        response = self.client.get(reverse("finance_guide"))

        self.assertEqual(response.status_code, 302)
