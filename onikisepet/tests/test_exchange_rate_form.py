from decimal import Decimal

from django.test import TestCase, override_settings

from onikisepet.forms import ExchangeRateForm


@override_settings(LANGUAGE_CODE="en")
class ExchangeRateFormTests(TestCase):
    def _data(self, **overrides):
        data = {
            "currency": "USD",
            "rate_to_base": Decimal("34.00"),
            "effective_date": "2026-09-01",
        }
        data.update(overrides)
        return data

    def test_valid_rate_is_accepted(self):
        self.assertTrue(ExchangeRateForm(data=self._data()).is_valid())

    def test_base_currency_is_not_offered_as_a_choice(self):
        """Storing a TRY-to-TRY rate would let someone rescale every TRY
        figure on the dashboard, so the base currency is not selectable.
        """
        choices = dict(ExchangeRateForm().fields["currency"].choices)

        self.assertNotIn("TRY", choices)
        self.assertIn("USD", choices)

    def test_base_currency_is_rejected_even_if_posted_directly(self):
        form = ExchangeRateForm(data=self._data(currency="TRY"))

        self.assertFalse(form.is_valid())
        self.assertIn("currency", form.errors)

    def test_zero_rate_is_rejected(self):
        form = ExchangeRateForm(data=self._data(rate_to_base=Decimal("0")))

        self.assertFalse(form.is_valid())
        self.assertIn("rate_to_base", form.errors)

    def test_negative_rate_is_rejected(self):
        form = ExchangeRateForm(data=self._data(rate_to_base=Decimal("-5")))

        self.assertFalse(form.is_valid())
        self.assertIn("rate_to_base", form.errors)

    def test_duplicate_rate_for_the_same_currency_and_date_is_rejected(self):
        ExchangeRateForm(data=self._data()).save()

        form = ExchangeRateForm(data=self._data())

        self.assertFalse(form.is_valid())
