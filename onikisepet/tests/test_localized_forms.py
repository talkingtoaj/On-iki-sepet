"""Amount fields must accept either numeric convention.

A Turkish treasurer types 1.234,56; an English-speaking one types 1234.56.
Rejecting either would push people into retyping amounts, which is exactly
where transcription errors come from.
"""

from decimal import Decimal

from django.test import TestCase, override_settings

from onikisepet.forms import (
    AccountForm,
    CashExpenseForm,
    ExchangeRateForm,
    TransactionForm,
)
from onikisepet.money_input import MoneyField

from .helpers import ReceiptFileTestMixin, TransactionTestMixin


class TransactionFormAmountTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("form_amount_user", is_superuser=True)
        self.account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.category = self.create_category(name="Donation", category_type="income")

    def _form(self, amount):
        return TransactionForm(
            data={
                "date": "2026-09-09",
                "amount": amount,
                "transaction_type": "income",
                "account": self.account.pk,
                "category": self.category.pk,
                "description": "",
            }
        )

    def test_turkish_amount_is_accepted(self):
        form = self._form("1.234,56")

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["amount"], Decimal("1234.56"))

    def test_plain_amount_is_accepted(self):
        form = self._form("1234.56")

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["amount"], Decimal("1234.56"))

    def test_comma_decimal_is_accepted(self):
        form = self._form("1234,56")

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["amount"], Decimal("1234.56"))

    def test_thousands_only_amount_is_accepted(self):
        form = self._form("1.234")

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["amount"], Decimal("1234"))

    def test_garbage_is_rejected_on_the_amount_field(self):
        form = self._form("bin lira")

        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_ambiguous_malformed_amount_is_rejected(self):
        form = self._form("1.2345")

        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_negative_amount_is_still_rejected(self):
        """The existing business rule must survive the new parsing."""
        form = self._form("-1.234,56")

        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)


class OtherFormAmountTests(
    ReceiptFileTestMixin, TransactionTestMixin, TestCase
):
    def setUp(self):
        self.cash_account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.expense_category = self.create_category(
            name="Supplies", category_type="expense"
        )

    def test_account_opening_balance_accepts_turkish_format(self):
        form = AccountForm(
            data={
                "name": "Yeni Hesap",
                "account_type": "bank",
                "account_purpose": "savings",
                "currency": "TRY",
                "opening_balance": "12.500,75",
                "is_active": "on",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["opening_balance"], Decimal("12500.75"))

    def test_cash_expense_accepts_turkish_format(self):
        form = CashExpenseForm(
            data={
                "date": "2026-09-09",
                "payee": "Migros",
                "amount": "1.234,56",
                "cash_account": self.cash_account.pk,
                "category": self.expense_category.pk,
                "description": "",
            },
            files={"receipt_file": self.make_receipt_file("receipt.jpg")},
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["amount"], Decimal("1234.56"))

    def test_exchange_rate_accepts_a_comma_decimal(self):
        form = ExchangeRateForm(
            data={
                "currency": "USD",
                "rate_to_base": "34,50",
                "effective_date": "2026-09-01",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["rate_to_base"], Decimal("34.50"))

    def test_exchange_rate_keeps_full_precision(self):
        """Rates carry six decimal places, so money's two-place rounding must
        not be applied to them.
        """
        form = ExchangeRateForm(
            data={
                "currency": "USD",
                "rate_to_base": "34,123456",
                "effective_date": "2026-09-01",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["rate_to_base"], Decimal("34.123456"))


class MoneyWidgetRenderingTests(TestCase):
    @override_settings(LANGUAGE_CODE="tr")
    def test_widget_renders_turkish_format(self):
        rendered = MoneyField().widget.render("amount", Decimal("1234.56"))

        self.assertIn("1.234,56", rendered)

    @override_settings(LANGUAGE_CODE="en")
    def test_widget_renders_english_format(self):
        rendered = MoneyField().widget.render("amount", Decimal("1234.56"))

        self.assertIn("1,234.56", rendered)

    def test_widget_echoes_back_unparseable_input(self):
        """After a validation error the user must see what they typed, not a
        blank box or a crash.
        """
        rendered = MoneyField().widget.render("amount", "bin lira")

        self.assertIn("bin lira", rendered)


class EditFormAmountDisplayTests(TransactionTestMixin, TestCase):
    """The edit form must show the existing amount in the reader's own
    convention, not a raw decimal, or a Turkish treasurer sees an unfamiliar
    format and is tempted to retype it.
    """

    def setUp(self):
        from onikisepet.usecases.roles import TREASURER

        self.user = self.create_user("edit_display_user", group_name=TREASURER)
        self.account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.category = self.create_category(name="Supplies", category_type="expense")
        self.transaction = self.create_transaction(
            transaction_type="expense",
            amount=Decimal("1500.00"),
            source_account=self.account,
            category=self.category,
            created_by=self.user,
        )
        self.client.login(username=self.user.username, password=self.password)

    def _edit_page(self, **kwargs):
        from django.urls import reverse

        return self.client.get(
            reverse("transaction_edit", args=[self.transaction.pk]), **kwargs
        )

    def test_turkish_reader_sees_the_turkish_convention(self):
        response = self._edit_page(headers={"accept-language": "tr"})

        self.assertContains(response, 'value="1.500,00"')

    @override_settings(LANGUAGE_CODE="en")
    def test_english_reader_sees_the_english_convention(self):
        response = self._edit_page()

        self.assertContains(response, 'value="1,500.00"')

    def test_the_round_trip_preserves_the_amount(self):
        """Whatever the form displays must parse back to the same figure."""
        from django.urls import reverse

        response = self._edit_page(headers={"accept-language": "tr"})
        displayed = "1.500,00"
        self.assertContains(response, displayed)

        self.client.post(
            reverse("transaction_edit", args=[self.transaction.pk]),
            {
                "date": str(self.transaction.date),
                "amount": displayed,
                "transaction_type": "expense",
                "payee": "",
                "account": self.account.pk,
                "category": self.category.pk,
                "description": "",
                "change_reason": "no change to the amount",
            },
        )

        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.amount, Decimal("1500.00"))
