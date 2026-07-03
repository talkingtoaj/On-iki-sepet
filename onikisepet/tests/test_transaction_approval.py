from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from onikisepet.models import Transaction
from onikisepet.usecases import approval

from .helpers import ProfileTestMixin, TransactionTestMixin


class TransactionApprovalRulesTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def setUp(self):
        self.admin_user = self.create_user("approval_admin", is_superuser=True)
        self.data_entry_user = self.create_user_with_profile(
            "approval_data_entry",
            role=self.ROLE_DATA_ENTRY,
        )
        self.cash_account = self.create_account(
            name="Approval Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.bank_account = self.create_account(
            name="Approval Bank",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Approval Income",
            category_type="income",
        )
        self.expense_category = self.create_category(
            name="Approval Expense",
            category_type="expense",
        )

    def test_transfer_created_by_admin_starts_pending(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            reverse("transfer_create"),
            data={
                "date": "2026-06-15",
                "amount": "100.00",
                "source_account": self.cash_account.pk,
                "target_account": self.bank_account.pk,
                "description": "Kasa → banka",
            },
        )

        self.assertRedirects(response, reverse("transaction_list"))
        transaction = Transaction.objects.get()
        self.assertEqual(transaction.approval_status, Transaction.ApprovalStatus.PENDING)

    def test_income_created_by_admin_is_auto_approved(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        self.client.post(
            reverse("cash_income_create"),
            data={
                "date": "2026-06-15",
                "donor_name": "Bağışçı",
                "amount": "250.00",
                "cash_account": self.cash_account.pk,
                "category": self.income_category.pk,
                "description": "",
            },
        )

        transaction = Transaction.objects.get()
        self.assertEqual(transaction.approval_status, Transaction.ApprovalStatus.APPROVED)

    def test_income_created_by_data_entry_starts_pending(self):
        self.client.login(
            username=self.data_entry_user.username,
            password=self.password,
        )

        self.client.post(
            reverse("cash_income_create"),
            data={
                "date": "2026-06-15",
                "donor_name": "Bağışçı",
                "amount": "250.00",
                "cash_account": self.cash_account.pk,
                "category": self.income_category.pk,
                "description": "",
            },
        )

        transaction = Transaction.objects.get()
        self.assertEqual(transaction.approval_status, Transaction.ApprovalStatus.PENDING)


class TransactionApprovalViewTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def setUp(self):
        self.admin_user = self.create_user("approval_view_admin", is_superuser=True)
        self.data_entry_user = self.create_user_with_profile(
            "approval_view_data_entry",
            role=self.ROLE_DATA_ENTRY,
        )
        self.cash_account = self.create_account(
            name="Approval View Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Approval View Income",
            category_type="income",
        )
        self.pending_transaction = self.create_transaction(
            transaction_type="income",
            amount=Decimal("100.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.data_entry_user,
            approval_status=Transaction.ApprovalStatus.PENDING,
        )

    def test_admin_can_approve_pending_transaction(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.post(
            reverse("transaction_approve", kwargs={"pk": self.pending_transaction.pk}),
        )

        self.assertRedirects(response, reverse("transaction_list"))
        self.pending_transaction.refresh_from_db()
        self.assertEqual(
            self.pending_transaction.approval_status,
            Transaction.ApprovalStatus.APPROVED,
        )

    def test_data_entry_cannot_approve_transaction(self):
        self.client.login(
            username=self.data_entry_user.username,
            password=self.password,
        )

        response = self.client.post(
            reverse("transaction_approve", kwargs={"pk": self.pending_transaction.pk}),
        )

        self.assertEqual(response.status_code, 403)


class TransactionApprovalReportTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def setUp(self):
        self.viewer_user = self.create_user_with_profile(
            "approval_report_viewer",
            role=self.ROLE_VIEWER,
        )
        self.cash_account = self.create_account(
            name="Approval Report Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Approval Report Income",
            category_type="income",
        )
        self.report_url = reverse("report_dashboard")

    def test_pending_income_is_excluded_from_report_totals(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("500.00"),
            target_account=self.cash_account,
            category=self.income_category,
            date="2026-06-10",
            created_by=self.viewer_user,
            approval_status=Transaction.ApprovalStatus.PENDING,
        )
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.report_url)

        self.assertContains(response, "Toplam Gelir: 0.00 TRY")

    def test_approved_income_is_included_in_report_totals(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("500.00"),
            target_account=self.cash_account,
            category=self.income_category,
            date="2026-06-10",
            created_by=self.viewer_user,
            approval_status=Transaction.ApprovalStatus.APPROVED,
        )
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.report_url)

        self.assertContains(response, "Toplam Gelir: 500.00 TRY")


class ApprovalUseCaseTests(TransactionTestMixin, TestCase):
    def test_initial_approval_status_for_transfer_is_pending(self):
        user = self.create_user("approval_usecase_admin", is_superuser=True)

        status = approval.initial_approval_status(
            user=user,
            transaction_type=Transaction.TransactionType.TRANSFER,
        )

        self.assertEqual(status, Transaction.ApprovalStatus.PENDING)

    def test_apply_initial_approval_sets_metadata_for_auto_approved_income(self):
        user = self.create_user("approval_usecase_apply_admin", is_superuser=True)
        cash_account = self.create_account(name="Apply Cash")
        income_category = self.create_category(name="Apply Income", category_type="income")
        transaction = Transaction(
            date="2026-06-15",
            amount=Decimal("100.00"),
            currency="TRY",
            transaction_type=Transaction.TransactionType.INCOME,
            target_account=cash_account,
            category=income_category,
            created_by=user,
        )

        approval.apply_initial_approval(transaction, user)

        self.assertEqual(transaction.approval_status, Transaction.ApprovalStatus.APPROVED)
        self.assertEqual(transaction.approved_by, user)
        self.assertIsNotNone(transaction.approved_at)


class TransactionApprovalBalanceTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user("approval_balance_user", is_superuser=True)
        self.cash_account = self.create_account(
            name="Approval Balance Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
            opening_balance=Decimal("1000.00"),
        )
        self.bank_account = self.create_account(
            name="Approval Balance Bank",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
            opening_balance=Decimal("500.00"),
        )
        self.calculations = self.get_financial_calculations_module()

    def test_pending_transfer_does_not_change_account_balances(self):
        self.create_transaction(
            transaction_type="transfer",
            amount=Decimal("100.00"),
            source_account=self.cash_account,
            target_account=self.bank_account,
            created_by=self.user,
            approval_status=Transaction.ApprovalStatus.PENDING,
        )

        self.assertEqual(
            self.calculations.calculate_account_balance(self.cash_account),
            Decimal("1000.00"),
        )

    def test_pending_income_does_not_increase_account_balance(self):
        income_category = self.create_category(name="Balance Income", category_type="income")
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("200.00"),
            target_account=self.cash_account,
            category=income_category,
            created_by=self.user,
            approval_status=Transaction.ApprovalStatus.PENDING,
        )

        self.assertEqual(
            self.calculations.calculate_account_balance(self.cash_account),
            Decimal("1000.00"),
        )
