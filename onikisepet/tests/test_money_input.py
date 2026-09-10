"""Tests for amount parsing.

Turkish convention writes one thousand two hundred as ``1.234,56``; plain input
writes ``1234.56``. Both must be accepted, and the genuinely ambiguous shapes
resolved by a rule rather than by luck, because getting this wrong misreads an
amount by a factor of a thousand.

The disambiguating rule: a money amount has at most two decimal places, and a
thousands group is exactly three digits. That is enough to settle every case.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from onikisepet.money_input import format_amount, parse_amount


@override_settings(LANGUAGE_CODE="en")
class ParseUnambiguousTests(TestCase):
    def test_plain_integer(self):
        self.assertEqual(parse_amount("1234"), Decimal("1234"))

    def test_plain_decimal_with_point(self):
        self.assertEqual(parse_amount("1234.56"), Decimal("1234.56"))

    def test_turkish_decimal_with_comma(self):
        self.assertEqual(parse_amount("1234,56"), Decimal("1234.56"))

    def test_turkish_full_format(self):
        self.assertEqual(parse_amount("1.234,56"), Decimal("1234.56"))

    def test_english_full_format(self):
        self.assertEqual(parse_amount("1,234.56"), Decimal("1234.56"))

    def test_turkish_millions(self):
        self.assertEqual(parse_amount("1.234.567,89"), Decimal("1234567.89"))

    def test_english_millions(self):
        self.assertEqual(parse_amount("1,234,567.89"), Decimal("1234567.89"))

    def test_single_decimal_place(self):
        self.assertEqual(parse_amount("12,5"), Decimal("12.5"))
        self.assertEqual(parse_amount("12.5"), Decimal("12.5"))

    def test_space_as_thousands_separator(self):
        self.assertEqual(parse_amount("1 234,56"), Decimal("1234.56"))

    def test_non_breaking_space_as_thousands_separator(self):
        self.assertEqual(parse_amount("1 234,56"), Decimal("1234.56"))

    def test_negative_amounts(self):
        self.assertEqual(parse_amount("-1.234,56"), Decimal("-1234.56"))

    def test_currency_suffix_is_ignored(self):
        for text in ["1.234,56 TL", "1.234,56 TRY", "1234.56 USD", "1.234,56₺"]:
            self.assertEqual(parse_amount(text), Decimal("1234.56"), text)

    def test_decimal_and_numeric_input_passes_through(self):
        self.assertEqual(parse_amount(Decimal("12.34")), Decimal("12.34"))
        self.assertEqual(parse_amount(1234), Decimal("1234"))


@override_settings(LANGUAGE_CODE="en")
class ParseAmbiguousTests(TestCase):
    """The cases a naive implementation gets wrong."""

    def test_dot_with_three_digits_is_thousands_not_a_decimal(self):
        """``1.234`` must be 1234.

        Read as a decimal it would be 1.234, which has three decimal places
        and so is not a valid money amount at all. The collaborator's
        implementation returned 1.234 here, understating the figure a
        thousandfold.
        """
        self.assertEqual(parse_amount("1.234"), Decimal("1234"))

    def test_comma_with_three_digits_is_thousands(self):
        self.assertEqual(parse_amount("1,234"), Decimal("1234"))

    def test_dot_with_two_digits_is_a_decimal(self):
        self.assertEqual(parse_amount("1.23"), Decimal("1.23"))

    def test_comma_with_two_digits_is_a_decimal(self):
        self.assertEqual(parse_amount("1,23"), Decimal("1.23"))

    def test_repeated_separators_are_thousands(self):
        self.assertEqual(parse_amount("1.234.567"), Decimal("1234567"))
        self.assertEqual(parse_amount("1,234,567"), Decimal("1234567"))

    def test_zero_prefixed_group_is_a_decimal(self):
        """``0.500`` is half a unit, not five hundred."""
        self.assertEqual(parse_amount("0.500"), Decimal("0.500"))
        self.assertEqual(parse_amount("0,500"), Decimal("0.500"))


@override_settings(LANGUAGE_CODE="en")
class ParseRejectionTests(TestCase):
    def _assert_rejected(self, text):
        with self.assertRaises(ValidationError, msg=f"should reject {text!r}"):
            parse_amount(text)

    def test_empty_input_is_rejected(self):
        for text in ["", "   ", None]:
            self._assert_rejected(text)

    def test_letters_are_rejected(self):
        for text in ["abc", "12abc", "bin lira"]:
            self._assert_rejected(text)

    def test_malformed_thousands_groups_are_rejected(self):
        """``1.2345`` is neither a valid money decimal nor a thousands group,
        so it is refused rather than guessed at.
        """
        for text in ["1.2345", "1,2345", "1.23.456", "12.34.56"]:
            self._assert_rejected(text)

    def test_multiple_decimal_separators_are_rejected(self):
        for text in ["1,23,45", "1.23.45"]:
            self._assert_rejected(text)

    def test_stray_separators_are_rejected(self):
        for text in [".", ",", "1.", "1,", ".5.5", "1..2"]:
            self._assert_rejected(text)


@override_settings(LANGUAGE_CODE="en")
class FormatAmountTests(TestCase):
    def test_turkish_formatting(self):
        self.assertEqual(format_amount(Decimal("1234.56"), "tr"), "1.234,56")

    def test_english_formatting(self):
        self.assertEqual(format_amount(Decimal("1234.56"), "en"), "1,234.56")

    def test_millions_are_grouped(self):
        self.assertEqual(format_amount(Decimal("1234567.89"), "tr"), "1.234.567,89")
        self.assertEqual(format_amount(Decimal("1234567.89"), "en"), "1,234,567.89")

    def test_negative_amounts(self):
        self.assertEqual(format_amount(Decimal("-1234.56"), "tr"), "-1.234,56")

    def test_small_amounts_are_not_grouped(self):
        self.assertEqual(format_amount(Decimal("12.30"), "tr"), "12,30")

    def test_blank_input_formats_as_empty(self):
        self.assertEqual(format_amount(None, "tr"), "")
        self.assertEqual(format_amount("", "tr"), "")

    def test_round_trip(self):
        for value in [Decimal("0.05"), Decimal("1234.56"), Decimal("1234567.89")]:
            for lang in ("tr", "en"):
                self.assertEqual(parse_amount(format_amount(value, lang)), value)


class DecimalPlaceSensitivityTests(TestCase):
    """The decimal-place allowance is what settles the ambiguous shapes, so a
    field permitting more precision reads the same text differently. This is
    deliberate, and pinned here so it cannot drift unnoticed.
    """

    def test_money_reads_a_three_digit_group_as_thousands(self):
        self.assertEqual(parse_amount("1.234", max_decimal_places=2), Decimal("1234"))

    def test_a_six_place_field_reads_it_as_a_decimal(self):
        self.assertEqual(
            parse_amount("1.234", max_decimal_places=6), Decimal("1.234")
        )

    def test_a_six_place_field_accepts_full_rate_precision(self):
        self.assertEqual(
            parse_amount("34,123456", max_decimal_places=6), Decimal("34.123456")
        )

    def test_money_still_rejects_excess_precision(self):
        with self.assertRaises(ValidationError):
            parse_amount("34,123456", max_decimal_places=2)

    def test_both_separators_still_work_at_six_places(self):
        self.assertEqual(
            parse_amount("1.234,567890", max_decimal_places=6),
            Decimal("1234.567890"),
        )
