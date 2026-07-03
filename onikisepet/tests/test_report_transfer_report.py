from datetime import date
from decimal import Decimal

from django.test import TestCase

from onikisepet.models import Transaction
from onikisepet.usecases import financial_calculations

from .helpers import TransactionTestMixin


class TransferReportTests(TransactionTestMixin, TestCase):
    """Bölüm 6: Transfer raporu — hesaplar arası hareketler, gelir/gidere dahil değil."""

    def setUp(self):
        self.user = self.create_user("transfer_report_user", is_superuser=True)
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

    def test_build_transfer_report_lists_only_transfer_transactions(self):
        transfer = self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("100.00"),
            source_account=self.bank,
            target_account=self.cash,
            description="Cash top-up",
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
            transaction_type="expense",
            amount=Decimal("75.00"),
            source_account=self.cash,
            category=self.expense_category,
            created_by=self.user,
        )

        report = financial_calculations.build_transfer_report(
            Transaction.objects.all()
        )

        self.assertEqual(len(report), 1)
        self.assertEqual(report[0]["amount"], transfer.amount)
        self.assertEqual(report[0]["source_account"], self.bank)
        self.assertEqual(report[0]["target_account"], self.cash)
        self.assertEqual(report[0]["description"], "Cash top-up")

    def test_build_transfer_report_returns_empty_list_when_no_transfers(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("200.00"),
            target_account=self.cash,
            category=self.income_category,
            created_by=self.user,
        )

        report = financial_calculations.build_transfer_report(
            Transaction.objects.all()
        )

        self.assertEqual(report, [])

    def test_build_transfer_report_orders_by_date_descending(self):
        older = self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("50.00"),
            source_account=self.bank,
            target_account=self.cash,
            description="Older transfer",
            date="2026-06-01",
            created_by=self.user,
        )
        newer = self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("75.00"),
            source_account=self.bank,
            target_account=self.cash,
            description="Newer transfer",
            date="2026-06-15",
            created_by=self.user,
        )

        report = financial_calculations.build_transfer_report(
            Transaction.objects.all()
        )

        self.assertEqual(report[0]["description"], newer.description)
        self.assertEqual(report[1]["description"], older.description)

    def test_build_transfer_report_respects_filtered_queryset(self):
        self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("50.00"),
            source_account=self.bank,
            target_account=self.cash,
            description="June transfer",
            date="2026-06-10",
            created_by=self.user,
        )
        self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("75.00"),
            source_account=self.bank,
            target_account=self.cash,
            description="July transfer",
            date="2026-07-10",
            created_by=self.user,
        )

        june_transactions = Transaction.objects.filter(
            date__gte=date(2026, 6, 1),
            date__lte=date(2026, 6, 30),
        )
        report = financial_calculations.build_transfer_report(june_transactions)

        self.assertEqual(len(report), 1)
        self.assertEqual(report[0]["description"], "June transfer")

    def test_build_transfer_summary_counts_only_transfers(self):
        self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("100.00"),
            source_account=self.bank,
            target_account=self.cash,
            created_by=self.user,
        )
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("500.00"),
            target_account=self.cash,
            category=self.income_category,
            created_by=self.user,
        )

        summary = financial_calculations.build_transfer_summary(
            Transaction.objects.all()
        )

        self.assertEqual(summary["TRY"], Decimal("100.00"))
        self.assertEqual(summary["USD"], Decimal("0.00"))

    def test_transfer_totals_do_not_affect_income_or_expense_totals(self):
        self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("100.00"),
            source_account=self.bank,
            target_account=self.cash,
            created_by=self.user,
        )
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("300.00"),
            target_account=self.cash,
            category=self.income_category,
            created_by=self.user,
        )
        self.create_transaction(
            transaction_type="expense",
            amount=Decimal("80.00"),
            source_account=self.cash,
            category=self.expense_category,
            created_by=self.user,
        )

        transactions = Transaction.objects.all()

        self.assertEqual(
            financial_calculations.calculate_income_total(transactions),
            Decimal("300.00"),
        )
        self.assertEqual(
            financial_calculations.calculate_expense_total(transactions),
            Decimal("80.00"),
        )
        self.assertEqual(
            financial_calculations.calculate_transfer_total_for_currency(
                transactions,
                "TRY",
            ),
            Decimal("100.00"),
        )
