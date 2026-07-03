from decimal import Decimal

from django.apps import apps
from django.test import TestCase
from django.urls import reverse

from .helpers import ProfileTestMixin, TransactionTestMixin


class AccountChangeRequestListUiTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def setUp(self):
        self.account = self.create_account(
            name="UI Change Account",
            opening_balance=Decimal("100.00"),
        )
        self.data_entry_user = self.create_user_with_profile(
            "acr_ui_data_entry",
            role=self.ROLE_DATA_ENTRY,
        )
        self.approver_user = self.create_data_entry_approver("acr_ui_approver")
        self.viewer_user = self.create_user_with_profile(
            "acr_ui_viewer",
            role=self.ROLE_VIEWER,
        )
        self.account_list_url = reverse("account_list")
        self.pending_list_url = reverse("account_change_request_list")
        self.change_request_model = apps.get_model("onikisepet", "AccountChangeRequest")

    def test_data_entry_sees_change_request_link_on_account_list(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.account_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ad değişikliği talep et")
        self.assertContains(
            response,
            reverse("account_change_request", kwargs={"pk": self.account.pk}),
        )

    def test_viewer_cannot_access_account_list(self):
        self.client.login(username=self.viewer_user.username, password=self.password)

        response = self.client.get(self.account_list_url)

        self.assertEqual(response.status_code, 403)

    def test_approver_sees_pending_change_request_list(self):
        self.change_request_model.objects.create(
            account=self.account,
            requested_by=self.data_entry_user,
            proposed_name="Pending Name",
        )
        self.client.login(username=self.approver_user.username, password=self.password)

        response = self.client.get(self.pending_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pending Name")
        self.assertContains(response, self.account.name)
        self.assertContains(response, self.data_entry_user.username)

    def test_approver_can_approve_change_request_from_list(self):
        change_request = self.change_request_model.objects.create(
            account=self.account,
            requested_by=self.data_entry_user,
            proposed_name="Approved From List",
        )
        self.client.login(username=self.approver_user.username, password=self.password)

        response = self.client.post(
            reverse(
                "account_change_request_approve",
                kwargs={"pk": change_request.pk},
            ),
        )

        self.assertRedirects(response, self.pending_list_url)
        self.account.refresh_from_db()
        self.assertEqual(self.account.name, "Approved From List")

    def test_approver_can_reject_change_request_with_reason(self):
        change_request = self.change_request_model.objects.create(
            account=self.account,
            requested_by=self.data_entry_user,
            proposed_name="Rejected Name",
        )
        self.client.login(username=self.approver_user.username, password=self.password)

        response = self.client.post(
            reverse(
                "account_change_request_reject",
                kwargs={"pk": change_request.pk},
            ),
            data={"rejection_reason": "İsim uygun değil"},
        )

        self.assertRedirects(response, self.pending_list_url)
        self.account.refresh_from_db()
        change_request.refresh_from_db()
        self.assertEqual(self.account.name, "UI Change Account")
        self.assertEqual(change_request.status, "rejected")
        self.assertEqual(change_request.rejection_reason, "İsim uygun değil")

    def test_plain_data_entry_cannot_access_pending_change_request_list(self):
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.get(self.pending_list_url)

        self.assertEqual(response.status_code, 403)

    def test_plain_data_entry_cannot_approve_change_request(self):
        change_request = self.change_request_model.objects.create(
            account=self.account,
            requested_by=self.data_entry_user,
            proposed_name="Should Not Apply",
        )
        self.client.login(username=self.data_entry_user.username, password=self.password)

        response = self.client.post(
            reverse(
                "account_change_request_approve",
                kwargs={"pk": change_request.pk},
            ),
        )

        self.assertEqual(response.status_code, 403)
        self.account.refresh_from_db()
        self.assertEqual(self.account.name, "UI Change Account")
