from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from onikisepet.models import Transaction

from .helpers import TransactionTestMixin


class HtmxTransactionListViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.htmx_url = reverse("htmx_transaction_list")
        self.admin_user = self.create_user("htmx_list_admin", is_superuser=True)
        self.viewer_user = self.create_user("htmx_list_viewer", group_name="Viewer")
        self.data_entry_user = self.create_user(
            "htmx_list_data_entry",
            group_name="Data Entry",
        )
        self.cash_account = self.create_account(
            name="Htmx Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Htmx Income",
            category_type="income",
        )

    def test_htmx_transaction_list_returns_partial_html(self):
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("50.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.admin_user,
        )
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.htmx_url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "transaction-table")
        self.assertNotContains(response, "<!DOCTYPE html>")

    def test_htmx_transaction_list_pending_filter(self):
        pending = self.create_transaction(
            transaction_type="income",
            amount=Decimal("10.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.data_entry_user,
            approval_status=Transaction.ApprovalStatus.PENDING,
            description="Pending only",
        )
        self.create_transaction(
            transaction_type="income",
            amount=Decimal("20.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.admin_user,
            approval_status=Transaction.ApprovalStatus.APPROVED,
            description="Approved only",
        )
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(
            self.htmx_url,
            {"status": "pending"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pending only")
        self.assertNotContains(response, "Approved only")

    def test_viewer_cannot_access_htmx_transaction_list(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.htmx_url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 403)


class HtmxReportDashboardViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.report_url = reverse("report_dashboard")
        self.admin_user = self.create_user("htmx_report_admin", is_superuser=True)

    def test_report_dashboard_returns_partial_on_hx_request(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(
            self.report_url,
            {"period": "this_month"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TRY Özeti")
        self.assertContains(response, 'id="report-range-label"')
        self.assertNotContains(response, "<!DOCTYPE html>")


class HtmxFinanceGuideViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.admin_user = self.create_user("htmx_finance_admin", is_superuser=True)
        self.guide_url = reverse("finance_guide")
        self.income_url = reverse("htmx_finance_income")
        self.expenses_url = reverse("htmx_finance_expenses")
        self.accounts_url = reverse("htmx_finance_accounts")

    def test_finance_guide_page_renders_buttons(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.guide_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bu ay gelirleri")
        self.assertContains(response, "finance-guide-content")

    def test_htmx_finance_income_returns_partial(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.income_url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bu Ay Gelirleri")
        self.assertNotContains(response, "<!DOCTYPE html>")

    def test_htmx_finance_expenses_returns_partial(self):
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.expenses_url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bu Ay Giderleri")
        self.assertNotContains(response, "<!DOCTYPE html>")

    def test_htmx_finance_accounts_returns_partial(self):
        self.create_account(
            name="Guide Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.accounts_url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hesap Bakiyeleri")
        self.assertContains(response, "Guide Cash")
        self.assertNotContains(response, "<!DOCTYPE html>")


class HtmxCurrencyDetailViewTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.admin_user = self.create_user("htmx_currency_admin", is_superuser=True)
        self.try_url = reverse("htmx_currency_detail", kwargs={"currency": "TRY"})

    def test_htmx_currency_detail_returns_try_content(self):
        self.create_account(
            name="TRY Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(self.try_url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TRY — Bu Ay Detay")
        self.assertContains(response, "htmx-panel")

    def test_htmx_currency_detail_invalid_currency_returns_404(self):
        invalid_url = reverse("htmx_currency_detail", kwargs={"currency": "GBP"})
        self.client.login(username=self.admin_user.username, password=self.password)

        response = self.client.get(invalid_url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 404)


class HtmxTransactionApprovalTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.approver_user = self.create_user("htmx_approval_admin", is_superuser=True)
        self.data_entry_user = self.create_user(
            "htmx_approval_data_entry",
            group_name="Data Entry",
        )
        self.cash_account = self.create_account(
            name="Htmx Approval Cash",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Htmx Approval Income",
            category_type="income",
        )
        self.pending_transaction = self.create_transaction(
            transaction_type="income",
            amount=Decimal("75.00"),
            target_account=self.cash_account,
            category=self.income_category,
            created_by=self.data_entry_user,
            approval_status=Transaction.ApprovalStatus.PENDING,
        )
        self.approve_url = reverse(
            "transaction_approve",
            kwargs={"pk": self.pending_transaction.pk},
        )
        self.reject_url = reverse(
            "transaction_reject",
            kwargs={"pk": self.pending_transaction.pk},
        )

    def test_htmx_approve_returns_updated_row_without_redirect(self):
        self.client.login(
            username=self.approver_user.username,
            password=self.password,
        )

        response = self.client.post(self.approve_url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "badge--approved")
        self.assertNotContains(response, 'class="approve-button"')
        self.pending_transaction.refresh_from_db()
        self.assertEqual(
            self.pending_transaction.approval_status,
            Transaction.ApprovalStatus.APPROVED,
        )

    def test_htmx_reject_returns_updated_row_without_redirect(self):
        self.client.login(
            username=self.approver_user.username,
            password=self.password,
        )

        response = self.client.post(
            self.reject_url,
            data={"rejection_reason": "Tutar hatalı"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "badge--rejected")
        self.pending_transaction.refresh_from_db()
        self.assertEqual(
            self.pending_transaction.approval_status,
            Transaction.ApprovalStatus.REJECTED,
        )

    def test_htmx_reject_get_returns_inline_form(self):
        self.client.login(
            username=self.approver_user.username,
            password=self.password,
        )

        response = self.client.get(self.reject_url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "transaction-reject-form")
        self.assertContains(response, "rejection_reason")

    def test_non_htmx_approve_still_redirects(self):
        self.client.login(
            username=self.approver_user.username,
            password=self.password,
        )

        response = self.client.post(self.approve_url)

        self.assertRedirects(response, reverse("transaction_list"))

    def test_data_entry_cannot_htmx_approve(self):
        self.client.login(
            username=self.data_entry_user.username,
            password=self.password,
        )

        response = self.client.post(self.approve_url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 403)
