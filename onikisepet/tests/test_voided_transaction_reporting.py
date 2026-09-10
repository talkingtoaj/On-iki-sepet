from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from onikisepet.usecases.roles import TREASURER

from .helpers import TransactionTestMixin


class VoidedTransactionsAreExcludedTests(TransactionTestMixin, TestCase):
    """A voided transaction stays in the database for the audit trail, but it
    must not reach any total or balance. The exclusion lives inside the
    calculation functions so that no caller can forget to apply it.
    """

    def setUp(self):
        self.user = self.create_user("void_report_user", group_name=TREASURER)
        self.account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
            opening_balance=Decimal("1000.00"),
        )
        self.other_account = self.create_account(
            name="Bank Account",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Donation",
            category_type="income",
        )
        self.expense_category = self.create_category(
            name="Supplies",
            category_type="expense",
        )
        self.calculations = self.get_financial_calculations_module()

    def _void(self, transaction, reason="entered twice"):
        transaction.is_void = True
        transaction.void_reason = reason
        transaction.voided_by = self.user
        transaction.save()
        return transaction

    def _all(self):
        return self.get_transaction_model().objects.all()

    def test_voided_income_is_excluded_from_income_totals(self):
        kept = self.create_transaction(
            transaction_type="income",
            amount=Decimal("500.00"),
            target_account=self.account,
            category=self.income_category,
            created_by=self.user,
        )
        self._void(
            self.create_transaction(
                transaction_type="income",
                amount=Decimal("300.00"),
                target_account=self.account,
                category=self.income_category,
                created_by=self.user,
            )
        )

        self.assertEqual(
            self.calculations.calculate_income_total(self._all()),
            kept.amount,
        )

    def test_voided_expense_is_excluded_from_expense_totals(self):
        self._void(
            self.create_transaction(
                transaction_type="expense",
                amount=Decimal("200.00"),
                source_account=self.account,
                category=self.expense_category,
                created_by=self.user,
            )
        )

        self.assertEqual(
            self.calculations.calculate_expense_total(self._all()),
            Decimal("0.00"),
        )

    def test_voided_transfer_is_excluded_from_transfer_totals(self):
        self._void(
            self.create_transaction(
                transaction_type="transfer",
                amount=Decimal("150.00"),
                source_account=self.account,
                target_account=self.other_account,
                created_by=self.user,
            )
        )

        self.assertEqual(
            self.calculations.calculate_transfer_total(self._all()),
            Decimal("0.00"),
        )

    def test_voided_income_is_excluded_from_per_currency_totals(self):
        self._void(
            self.create_transaction(
                transaction_type="income",
                amount=Decimal("300.00"),
                target_account=self.account,
                category=self.income_category,
                created_by=self.user,
            )
        )

        totals = self.calculations.calculate_income_total_by_currency(self._all())

        self.assertEqual(totals.get("TRY", Decimal("0.00")), Decimal("0.00"))

    def test_voided_transaction_does_not_change_an_account_balance(self):
        self._void(
            self.create_transaction(
                transaction_type="expense",
                amount=Decimal("250.00"),
                source_account=self.account,
                category=self.expense_category,
                created_by=self.user,
            )
        )

        self.assertEqual(
            self.calculations.calculate_account_balance(self.account),
            Decimal("1000.00"),
        )

    def test_voiding_a_transfer_restores_both_account_balances(self):
        transfer = self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("400.00"),
            source_account=self.account,
            target_account=self.other_account,
            created_by=self.user,
        )
        self.assertEqual(
            self.calculations.calculate_account_balance(self.account),
            Decimal("600.00"),
        )

        self._void(transfer)

        self.assertEqual(
            self.calculations.calculate_account_balance(self.account),
            Decimal("1000.00"),
        )
        self.assertEqual(
            self.calculations.calculate_account_balance(self.other_account),
            Decimal("0.00"),
        )

    def test_voided_transaction_is_excluded_from_the_currency_summary(self):
        self._void(
            self.create_transaction(
                transaction_type="income",
                amount=Decimal("300.00"),
                target_account=self.account,
                category=self.income_category,
                created_by=self.user,
            )
        )

        summaries = self.calculations.summarise_by_currency(self._all())

        for summary in summaries:
            self.assertEqual(summary.income, Decimal("0.00"))

    def test_dashboard_figures_ignore_a_voided_transaction(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("500.00"),
            target_account=self.account,
            category=self.income_category,
            created_by=self.user,
        )
        self._void(
            self.create_transaction(
                transaction_type="income",
                amount=Decimal("300.00"),
                target_account=self.account,
                category=self.income_category,
                created_by=self.user,
            )
        )
        self.client.login(username=self.user.username, password=self.password)

        response = self.client.get(reverse("report_dashboard"))

        self.assertContains(response, "500.00")
        self.assertNotContains(response, "800.00")
