from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from onikisepet.forms import CashIncomeForm, TransactionEditForm
from onikisepet.money_input import format_turkish_decimal, parse_localized_decimal

from .helpers import TransactionTestMixin


class ParseLocalizedDecimalTests(SimpleTestCase):
    def test_parses_turkish_format_with_thousands(self):
        self.assertEqual(parse_localized_decimal("1.250,50"), Decimal("1250.50"))

    def test_parses_comma_decimal_without_thousands(self):
        self.assertEqual(parse_localized_decimal("125,50"), Decimal("125.50"))

    def test_parses_dot_decimal_format(self):
        self.assertEqual(parse_localized_decimal("125.50"), Decimal("125.50"))

    def test_strips_currency_suffix(self):
        self.assertEqual(parse_localized_decimal("1.200,00 TL"), Decimal("1200.00"))


class FormatTurkishDecimalTests(SimpleTestCase):
    def test_formats_with_thousands_and_comma_decimal(self):
        self.assertEqual(format_turkish_decimal(Decimal("1250.50")), "1.250,50")

    def test_formats_small_amount(self):
        self.assertEqual(format_turkish_decimal(Decimal("500")), "500,00")


class TransactionAmountFieldTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("money_input_user", group_name="Data Entry")
        self.cash_account = self.create_account(
            name="Money Input Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Money Input Income",
            category_type="income",
        )

    def test_cash_income_form_accepts_turkish_amount(self):
        form = CashIncomeForm(
            data={
                "date": "2026-06-13",
                "donor_name": "Ahmet Yılmaz",
                "amount": "1.250,50",
                "cash_account": self.cash_account.pk,
                "category": self.income_category.pk,
                "description": "",
            },
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["amount"], Decimal("1250.50"))

    def test_cash_income_form_rejects_invalid_amount(self):
        form = CashIncomeForm(
            data={
                "date": "2026-06-13",
                "donor_name": "Ahmet Yılmaz",
                "amount": "abc",
                "cash_account": self.cash_account.pk,
                "category": self.income_category.pk,
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_transaction_edit_form_initial_amount_uses_turkish_format(self):
        transaction = self.create_transaction(
            transaction_type="income",
            amount=Decimal("1250.50"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.user,
            approval_status="pending",
        )

        form = TransactionEditForm(instance=transaction)

        self.assertEqual(form.initial["amount"], "1.250,50")
