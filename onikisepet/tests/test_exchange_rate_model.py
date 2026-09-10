from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from .helpers import ExchangeRateTestMixin


class ExchangeRateModelTests(ExchangeRateTestMixin, TestCase):
    """The ExchangeRate model stores what one unit of a foreign currency is
    worth in the base currency (TRY) on a given day. Reports use it to build a
    converted grand total, so a wrong or missing rate must never pass silently.
    """

    def test_exchange_rate_model_exists(self):
        self.assertIsNotNone(self.get_exchange_rate_model())

    def test_exchange_rate_stores_currency_rate_and_effective_date(self):
        rate = self.create_exchange_rate(
            currency="USD",
            rate_to_base=Decimal("34.500000"),
            effective_date="2026-09-01",
        )

        rate.refresh_from_db()

        self.assertEqual(rate.currency, "USD")
        self.assertEqual(rate.rate_to_base, Decimal("34.500000"))
        self.assertEqual(rate.effective_date, date(2026, 9, 1))

    def test_exchange_rate_rejects_duplicate_currency_on_the_same_date(self):
        self.create_exchange_rate(currency="USD", effective_date="2026-09-01")

        with self.assertRaises(ValidationError):
            self.create_exchange_rate(currency="USD", effective_date="2026-09-01")

    def test_exchange_rate_allows_same_currency_on_different_dates(self):
        self.create_exchange_rate(currency="USD", effective_date="2026-09-01")
        self.create_exchange_rate(currency="USD", effective_date="2026-09-02")

        self.assertEqual(self.get_exchange_rate_model().objects.count(), 2)

    def test_exchange_rate_rejects_zero_rate(self):
        with self.assertRaises(ValidationError):
            self.create_exchange_rate(rate_to_base=Decimal("0"))

    def test_exchange_rate_rejects_negative_rate(self):
        with self.assertRaises(ValidationError):
            self.create_exchange_rate(rate_to_base=Decimal("-1.00"))

    def test_exchange_rate_rejects_the_base_currency(self):
        """A TRY-to-TRY rate is always 1 and must not be stored, otherwise
        someone could enter a rate that silently rescales every TRY figure.
        """
        with self.assertRaises(ValidationError):
            self.create_exchange_rate(currency="TRY")

    def test_rate_for_returns_one_for_the_base_currency(self):
        model = self.get_exchange_rate_model()

        self.assertEqual(model.rate_for("TRY", date(2026, 9, 9)), Decimal("1"))

    def test_rate_for_returns_the_most_recent_rate_on_or_before_the_date(self):
        model = self.get_exchange_rate_model()
        self.create_exchange_rate(
            currency="USD",
            rate_to_base=Decimal("30.00"),
            effective_date="2026-08-01",
        )
        self.create_exchange_rate(
            currency="USD",
            rate_to_base=Decimal("34.00"),
            effective_date="2026-09-01",
        )
        self.create_exchange_rate(
            currency="USD",
            rate_to_base=Decimal("99.00"),
            effective_date="2026-10-01",
        )

        self.assertEqual(model.rate_for("USD", date(2026, 9, 9)), Decimal("34.00"))

    def test_rate_for_returns_none_when_no_rate_exists_on_or_before_the_date(self):
        model = self.get_exchange_rate_model()
        self.create_exchange_rate(currency="USD", effective_date="2026-09-01")

        self.assertIsNone(model.rate_for("USD", date(2026, 8, 1)))

    def test_rate_for_returns_none_for_a_currency_with_no_rates(self):
        model = self.get_exchange_rate_model()

        self.assertIsNone(model.rate_for("EUR", date(2026, 9, 9)))

    def test_quote_for_returns_the_row_so_reports_can_show_provenance(self):
        model = self.get_exchange_rate_model()
        self.create_exchange_rate(
            currency="USD",
            rate_to_base=Decimal("34.00"),
            effective_date="2026-09-01",
        )

        quote = model.quote_for("USD", date(2026, 9, 9))

        self.assertIsNotNone(quote)
        self.assertEqual(quote.rate_to_base, Decimal("34.00"))
        self.assertEqual(quote.effective_date, date(2026, 9, 1))

    def test_str_shows_the_currency_rate_and_date(self):
        rate = self.create_exchange_rate(
            currency="USD",
            rate_to_base=Decimal("34.00"),
            effective_date="2026-09-01",
        )

        self.assertIn("USD", str(rate))
        self.assertIn("2026-09-01", str(rate))
