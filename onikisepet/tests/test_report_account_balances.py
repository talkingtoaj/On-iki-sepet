from decimal import Decimal

from django.test import TestCase

from onikisepet.models import Transaction
from onikisepet.usecases import financial_calculations

from .helpers import TransactionTestMixin


class ReportAccountBalanceTests(TransactionTestMixin, TestCase):
    """Bölüm 6: Hesap bakiyeleri — mevcut bakiye, tüm onaylı işlemlerden hesaplanır."""

    def setUp(self):
        self.user = self.create_user("report_balance_user", is_superuser=True)
        self.cash = self.create_account(
            name="Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
            opening_balance=Decimal("1000.00"),
        )
        self.bank = self.create_account(
            name="Bank",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
            opening_balance=Decimal("500.00"),
        )
        self.income_category = self.create_category(name="Donation", category_type="income")
        self.expense_category = self.create_category(name="Rent", category_type="expense")

    def test_current_balance_starts_from_opening_balance(self):
        balance = financial_calculations.calculate_account_balance(self.cash)

        self.assertEqual(balance, Decimal("1000.00"))

    def test_current_balance_includes_income_expense_and_transfers(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("200.00"),
            target_account=self.cash,
            category=self.income_category,
            created_by=self.user,
        )
        self.create_transaction(
            transaction_type="expense",
            amount=Decimal("50.00"),
            source_account=self.cash,
            category=self.expense_category,
            created_by=self.user,
        )
        self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("25.00"),
            source_account=self.cash,
            target_account=self.bank,
            created_by=self.user,
        )

        cash_balance = financial_calculations.calculate_account_balance(self.cash)
        bank_balance = financial_calculations.calculate_account_balance(self.bank)

        self.assertEqual(cash_balance, Decimal("1125.00"))
        self.assertEqual(bank_balance, Decimal("525.00"))

    def test_current_balance_excludes_pending_transactions(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("200.00"),
            target_account=self.cash,
            category=self.income_category,
            approval_status=Transaction.ApprovalStatus.PENDING,
            created_by=self.user,
        )

        balance = financial_calculations.calculate_account_balance(self.cash)

        self.assertEqual(balance, Decimal("1000.00"))

    def test_period_balance_differs_from_current_balance_when_queryset_is_filtered(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("200.00"),
            target_account=self.cash,
            category=self.income_category,
            date="2026-06-10",
            created_by=self.user,
        )
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("300.00"),
            target_account=self.cash,
            category=self.income_category,
            date="2026-07-10",
            created_by=self.user,
        )

        june_transactions = Transaction.objects.filter(
            date__gte="2026-06-01",
            date__lte="2026-06-30",
        )

        current_balance = financial_calculations.calculate_account_balance(self.cash)
        period_balance = financial_calculations.calculate_account_balance_for_transactions(
            self.cash,
            june_transactions,
        )

        self.assertEqual(current_balance, Decimal("1500.00"))
        self.assertEqual(period_balance, Decimal("1200.00"))

    def test_report_should_use_current_balance_not_period_balance(self):
        """Rapor ekranı mevcut bakiye göstermeli; dönem filtresi bakiyeyi değiştirmemeli."""
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("200.00"),
            target_account=self.cash,
            category=self.income_category,
            date="2026-06-10",
            created_by=self.user,
        )

        empty_period = Transaction.objects.filter(date__gte="2099-01-01")
        period_balance = financial_calculations.calculate_account_balance_for_transactions(
            self.cash,
            empty_period,
        )
        current_balance = financial_calculations.calculate_account_balance(self.cash)

        self.assertEqual(period_balance, Decimal("1000.00"))
        self.assertEqual(current_balance, Decimal("1200.00"))
