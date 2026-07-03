from decimal import Decimal

from django.apps import apps
from django.test import TestCase
from django.urls import reverse

from onikisepet.models import Account

from .helpers import ProfileTestMixin, TransactionTestMixin


class AccountChangeRequestModelTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.change_request_model = apps.get_model("onikisepet", "AccountChangeRequest")

    def test_account_change_request_model_exists(self):
        self.assertIsNotNone(self.change_request_model)

    def test_change_request_defaults_to_pending(self):
        account = self.create_account(name="Change Request Account")
        requester = self.create_user_with_profile(
            "change_request_requester",
            role=self.ROLE_DATA_ENTRY,
        )

        change_request = self.change_request_model.objects.create(
            account=account,
            requested_by=requester,
            proposed_name="Updated Account Name",
        )

        self.assertEqual(change_request.status, "pending")

    def test_approved_change_request_applies_proposed_name(self):
        account = self.create_account(name="Before Approval Name")
        requester = self.create_user_with_profile(
            "change_request_approver_flow",
            role=self.ROLE_DATA_ENTRY,
        )
        approver = self.create_data_entry_approver("change_request_approver_user")
        change_request = self.change_request_model.objects.create(
            account=account,
            requested_by=requester,
            proposed_name="After Approval Name",
        )

        from onikisepet.usecases import account_changes

        account_changes.approve_change_request(change_request, approver)

        account.refresh_from_db()
        change_request.refresh_from_db()
        self.assertEqual(account.name, "After Approval Name")
        self.assertEqual(change_request.status, "approved")

    def test_rejected_change_request_does_not_apply_proposed_name(self):
        account = self.create_account(name="Rejected Change Name")
        requester = self.create_user_with_profile(
            "change_request_reject_flow",
            role=self.ROLE_DATA_ENTRY,
        )
        approver = self.create_user("change_request_reject_admin", is_superuser=True)
        change_request = self.change_request_model.objects.create(
            account=account,
            requested_by=requester,
            proposed_name="Should Not Apply",
        )

        from onikisepet.usecases import account_changes

        account_changes.reject_change_request(
            change_request,
            approver,
            reason="İsim uygun değil",
        )

        account.refresh_from_db()
        change_request.refresh_from_db()
        self.assertEqual(account.name, "Rejected Change Name")
        self.assertEqual(change_request.status, "rejected")


class AccountChangeRequestViewTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def setUp(self):
        self.account = self.create_account(
            name="View Change Account",
            opening_balance=Decimal("100.00"),
        )
        self.data_entry_user = self.create_user_with_profile(
            "change_request_view_data_entry",
            role=self.ROLE_DATA_ENTRY,
        )
        self.approver_user = self.create_data_entry_approver("change_request_view_approver")

    def test_data_entry_can_request_account_name_change(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.post(
            reverse("account_change_request", kwargs={"pk": self.account.pk}),
            data={"proposed_name": "Requested New Name"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.account.name, "View Change Account")

    def test_approver_can_approve_account_change_request(self):
        change_request_model = apps.get_model("onikisepet", "AccountChangeRequest")
        change_request = change_request_model.objects.create(
            account=self.account,
            requested_by=self.data_entry_user,
            proposed_name="Approver Applied Name",
        )
        self.client.login(username=self.approver_user.username, password=self.password)

        response = self.client.post(
            reverse(
                "account_change_request_approve",
                kwargs={"pk": change_request.pk},
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.account.refresh_from_db()
        self.assertEqual(self.account.name, "Approver Applied Name")
