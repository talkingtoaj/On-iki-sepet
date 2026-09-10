# These tests assert the English wording of the interface. The app now
# defaults to Turkish, so the language is pinned here rather than left
# implicit; Turkish rendering is covered in test_localization.py.
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from onikisepet.usecases.roles import TREASURER
from onikisepet.views import TRANSACTIONS_PER_PAGE

from .helpers import TransactionTestMixin


@override_settings(LANGUAGE_CODE="en")
class TransactionListPaginationTests(TransactionTestMixin, TestCase):
    """The list used to fetch every transaction with no limit, which would
    degrade steadily as the ledger grows.
    """

    def setUp(self):
        self.user = self.create_user("pagination_user", group_name=TREASURER)
        self.account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.category = self.create_category(name="Donation", category_type="income")
        self.url = reverse("transaction_list")
        self.client.login(username=self.user.username, password=self.password)

    def _create_many(self, count):
        for index in range(count):
            self.create_transaction(
                transaction_type="income",
                amount=Decimal("10.00"),
                target_account=self.account,
                category=self.category,
                description=f"Gift {index}",
                created_by=self.user,
            )

    def test_a_short_list_shows_everything_on_one_page(self):
        self._create_many(3)

        response = self.client.get(self.url)

        self.assertEqual(len(response.context["transactions"]), 3)

    def test_a_long_list_is_capped_at_the_page_size(self):
        self._create_many(TRANSACTIONS_PER_PAGE + 5)

        response = self.client.get(self.url)

        self.assertEqual(
            len(response.context["transactions"]), TRANSACTIONS_PER_PAGE
        )

    def test_the_second_page_holds_the_remainder(self):
        self._create_many(TRANSACTIONS_PER_PAGE + 5)

        response = self.client.get(self.url, {"page": 2})

        self.assertEqual(len(response.context["transactions"]), 5)

    def test_an_out_of_range_page_falls_back_to_the_last_page(self):
        self._create_many(3)

        response = self.client.get(self.url, {"page": 99})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["transactions"]), 3)

    def test_a_non_numeric_page_falls_back_to_the_first_page(self):
        self._create_many(3)

        response = self.client.get(self.url, {"page": "abc"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 1)

    def test_pagination_controls_appear_when_there_is_more_than_one_page(self):
        self._create_many(TRANSACTIONS_PER_PAGE + 5)

        response = self.client.get(self.url)

        self.assertContains(response, "page=2")

    def test_the_list_does_not_issue_a_query_per_row(self):
        """The query count must not grow with the number of rows.

        Asserting a constant rather than a specific number keeps the test
        about the N+1 hazard itself, so it will not churn when an unrelated
        query is added or removed elsewhere.
        """
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        self._create_many(3)
        with CaptureQueriesContext(connection) as few:
            self.client.get(self.url)

        self._create_many(40)
        with CaptureQueriesContext(connection) as many:
            self.client.get(self.url)

        self.assertEqual(len(many), len(few))
