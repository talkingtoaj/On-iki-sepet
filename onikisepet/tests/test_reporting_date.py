from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from onikisepet.usecases import financial_calculations
from onikisepet.usecases.roles import TREASURER

from .helpers import ExchangeRateTestMixin, TransactionTestMixin


class ReportingDateTests(ExchangeRateTestMixin, TransactionTestMixin, TestCase):
    """Which day a report is valued on decides which exchange rate applies, so
    it must come from Django's configured timezone rather than the machine's
    own clock. Otherwise the same data reports differently depending on where
    the server happens to run.
    """

    def test_today_follows_djangos_configured_timezone(self):
        self.assertEqual(financial_calculations.today(), timezone.localdate())

    @override_settings(TIME_ZONE="Pacific/Kiritimati")
    def test_today_tracks_a_timezone_change(self):
        self.assertEqual(financial_calculations.today(), timezone.localdate())

    def test_convert_to_base_defaults_to_todays_rate(self):
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

        with patch.object(
            financial_calculations, "today", return_value=date(2026, 8, 15)
        ):
            converted = financial_calculations.convert_to_base(
                Decimal("100.00"), "USD"
            )

        self.assertEqual(converted, Decimal("3000.00"))

    def test_grand_total_defaults_to_todays_rate(self):
        self.create_exchange_rate(
            currency="USD",
            rate_to_base=Decimal("34.00"),
            effective_date="2026-09-01",
        )

        with patch.object(
            financial_calculations, "today", return_value=date(2026, 8, 1)
        ):
            grand_total = financial_calculations.calculate_grand_total_in_base(
                {"USD": Decimal("100.00")}
            )

        self.assertFalse(grand_total.is_complete)
        self.assertEqual(grand_total.missing_currencies, ["USD"])

    def test_dashboard_reports_the_date_it_was_valued_on(self):
        user = self.create_user("reporting_date_user", group_name=TREASURER)
        self.client.login(username=user.username, password=self.password)

        response = self.client.get(reverse("report_dashboard"))

        self.assertEqual(response.context["as_of"], timezone.localdate())
