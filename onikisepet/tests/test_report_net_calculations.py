from decimal import Decimal

from django.test import TestCase

from onikisepet.models import Transaction
from onikisepet.usecases import financial_calculations

from .helpers import TransactionTestMixin


class ReportNetCalculationTests(TransactionTestMixin, TestCase):
    """Bölüm 6: Gelir, gider ve net durum — transferler nete dahil edilmez."""

    def setUp(self):
        self.user = self.create_user("report_net_user", is_superuser=True)
        self.cash = self.create_account(
            name="Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.bank = self.create_account(
            name="Bank",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.income_category = self.create_category(name="Donation", category_type="income")
        self.expense_category = self.create_category(name="Rent", category_type="expense")

    def test_income_total_counts_only_income_transactions(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("500.00"),
            target_account=self.cash,
            category=self.income_category,
            created_by=self.user,
        )
        self.create_transaction(
            transaction_type="expense",
            amount=Decimal("200.00"),
            source_account=self.cash,
            category=self.expense_category,
            created_by=self.user,
        )
        self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("100.00"),
            source_account=self.cash,
            target_account=self.bank,
            created_by=self.user,
        )

        total = financial_calculations.calculate_income_total(
            Transaction.objects.all()
        )

        self.assertEqual(total, Decimal("500.00"))

    def test_expense_total_counts_only_expense_transactions(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("500.00"),
            target_account=self.cash,
            category=self.income_category,
            created_by=self.user,
        )
        self.create_transaction(
            transaction_type="expense",
            amount=Decimal("200.00"),
            source_account=self.cash,
            category=self.expense_category,
            created_by=self.user,
        )
        self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("100.00"),
            source_account=self.cash,
            target_account=self.bank,
            created_by=self.user,
        )

        total = financial_calculations.calculate_expense_total(
            Transaction.objects.all()
        )

        self.assertEqual(total, Decimal("200.00"))

    def test_net_status_is_income_minus_expense(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("500.00"),
            target_account=self.cash,
            category=self.income_category,
            created_by=self.user,
        )
        self.create_transaction(
            transaction_type="expense",
            amount=Decimal("200.00"),
            source_account=self.cash,
            category=self.expense_category,
            created_by=self.user,
        )

        transactions = Transaction.objects.all()
        net = financial_calculations.calculate_net_status_for_currency(
            transactions,
            "TRY",
        )

        self.assertEqual(net, Decimal("300.00"))

    def test_net_status_ignores_transfers(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("500.00"),
            target_account=self.cash,
            category=self.income_category,
            created_by=self.user,
        )
        self.create_transaction(
            transaction_type="expense",
            amount=Decimal("200.00"),
            source_account=self.cash,
            category=self.expense_category,
            created_by=self.user,
        )
        self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("1000.00"),
            source_account=self.cash,
            target_account=self.bank,
            created_by=self.user,
        )

        transactions = Transaction.objects.all()
        net = financial_calculations.calculate_net_status_for_currency(
            transactions,
            "TRY",
        )

        self.assertEqual(net, Decimal("300.00"))

    def test_currency_summary_net_matches_income_minus_expense_per_currency(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("500.00"),
            target_account=self.cash,
            category=self.income_category,
            created_by=self.user,
        )
        self.create_transaction(
            transaction_type="expense",
            amount=Decimal("200.00"),
            source_account=self.cash,
            category=self.expense_category,
            created_by=self.user,
        )

        summary = financial_calculations.build_currency_summary(
            Transaction.objects.all()
        )

        self.assertEqual(summary["TRY"]["total_income"], Decimal("500.00"))
        self.assertEqual(summary["TRY"]["total_expenses"], Decimal("200.00"))
        self.assertEqual(summary["TRY"]["net_financial_status"], Decimal("300.00"))

    def test_expense_totals_by_category_include_only_expense_transactions(self):
        bills = self.create_category(name="Bills", category_type="expense")
        self.create_transaction(
            transaction_type="expense",
            amount=Decimal("250.00"),
            source_account=self.cash,
            category=self.expense_category,
            created_by=self.user,
        )
        self.create_transaction(
            transaction_type="expense",
            amount=Decimal("75.00"),
            source_account=self.cash,
            category=bills,
            created_by=self.user,
        )
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("500.00"),
            target_account=self.cash,
            category=self.income_category,
            created_by=self.user,
        )
        self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("100.00"),
            source_account=self.cash,
            target_account=self.bank,
            created_by=self.user,
        )

        totals = financial_calculations.calculate_expense_totals_by_category(
            Transaction.objects.all()
        )
        total_by_name = {item["category"].name: item["total"] for item in totals}

        self.assertEqual(total_by_name["Rent"], Decimal("250.00"))
        self.assertEqual(total_by_name["Bills"], Decimal("75.00"))
        self.assertNotIn("Donation", total_by_name)
