"""The import wizard: upload, review, confirm.

The shape being protected here is that nothing reaches the ledger until a
human confirms. An import that posted transactions on upload would be very
hard to undo, because each one would need voiding individually.
"""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from onikisepet.models import (
    BankStatementImport,
    BankStatementRow,
    Transaction,
    TransactionAuditLog,
)
from onikisepet.usecases import bank_ops
from onikisepet.usecases.roles import DATA_ENTRY, TREASURER, VIEWER

from .helpers import TransactionTestMixin

STATEMENT = (
    "Tarih,Açıklama,Tutar\n"
    "01/09/2026,Kira ödemesi,-1500.00\n"
    "02/09/2026,Bağış,2750.50\n"
)


def upload(text=STATEMENT, name="ekstre.csv"):
    return SimpleUploadedFile(name, text.encode("utf-8"), content_type="text/csv")


@override_settings(LANGUAGE_CODE="en")
class ImportWizardTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.treasurer = self.create_user("imp_treasurer", group_name=TREASURER)
        self.data_entry = self.create_user("imp_entry", group_name=DATA_ENTRY)
        self.viewer = self.create_user("imp_viewer", group_name=VIEWER)

        self.account = self.create_account(
            name="Garanti - Ana Gider",
            account_type="bank",
            account_purpose="main_expense",
            currency="TRY",
        )
        self.income_category = self.create_category(
            name="Bağış", category_type="income"
        )
        self.expense_category = self.create_category(
            name="Kira", category_type="expense"
        )
        self.client.login(username=self.treasurer.username, password=self.password)

    def _upload(self, text=STATEMENT, name="ekstre.csv"):
        return self.client.post(
            reverse("import_new"),
            {"account": self.account.pk, "statement_file": upload(text, name)},
        )

    def _draft(self):
        self._upload()
        return BankStatementImport.objects.get()

    def _confirm_payload(self, statement_import, **overrides):
        payload = {"action": "confirm"}
        for row in statement_import.rows.all():
            category = (
                self.income_category
                if row.transaction_type == "income"
                else self.expense_category
            )
            payload[f"category_{row.pk}"] = category.pk
        payload.update(overrides)
        return payload

    # --- upload -----------------------------------------------------------

    def test_upload_creates_a_draft_and_posts_nothing(self):
        response = self._upload()

        statement_import = BankStatementImport.objects.get()
        self.assertRedirects(
            response, reverse("import_preview", args=[statement_import.pk])
        )
        self.assertTrue(statement_import.is_draft)
        self.assertEqual(statement_import.rows.count(), 2)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_parsed_rows_carry_the_statement_values(self):
        statement_import = self._draft()

        first = statement_import.rows.get(row_number=1)
        self.assertEqual(first.date, date(2026, 9, 1))
        self.assertEqual(first.amount, Decimal("1500.00"))
        self.assertEqual(first.transaction_type, "expense")
        self.assertEqual(first.currency, "TRY")

    def test_a_credit_becomes_income(self):
        statement_import = self._draft()

        second = statement_import.rows.get(row_number=2)
        self.assertEqual(second.transaction_type, "income")
        self.assertEqual(second.amount, Decimal("2750.50"))

    def test_an_unreadable_file_is_reported_without_creating_a_draft(self):
        response = self._upload(text="nothing useful here\n")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "could not be read")
        self.assertEqual(BankStatementImport.objects.count(), 0)

    def test_an_unsupported_file_type_is_reported(self):
        response = self._upload(name="ekstre.docx")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(BankStatementImport.objects.count(), 0)

    def test_a_row_in_another_currency_is_flagged_not_imported(self):
        """Posting a USD line to a TRY account would corrupt the ledger."""
        self._upload(
            text=(
                "Tarih,Açıklama,Tutar,Para Birimi\n"
                "01/09/2026,Wire,-100.00,USD\n"
            )
        )
        statement_import = BankStatementImport.objects.get()

        row = statement_import.rows.get(row_number=1)
        self.assertTrue(row.parse_error)
        self.assertFalse(row.is_importable)

    # --- review -----------------------------------------------------------

    def test_preview_lists_the_rows(self):
        statement_import = self._draft()

        response = self.client.get(
            reverse("import_preview", args=[statement_import.pk])
        )

        self.assertContains(response, "Kira ödemesi")
        self.assertContains(response, "Bağış")

    def test_preview_offers_categories_matching_each_row_direction(self):
        """An expense line must not offer income categories: choosing one
        would fail model validation at confirmation time, after the reviewer
        thought they were finished.
        """
        statement_import = self._draft()
        expense_row = statement_import.rows.get(row_number=1)
        income_row = statement_import.rows.get(row_number=2)

        html = self.client.get(
            reverse("import_preview", args=[statement_import.pk])
        ).content.decode()

        expense_select = html.split(f'name="category_{expense_row.pk}"')[1].split(
            "</select>"
        )[0]
        income_select = html.split(f'name="category_{income_row.pk}"')[1].split(
            "</select>"
        )[0]

        self.assertIn("Kira", expense_select)
        self.assertNotIn("Bağış", expense_select)
        self.assertIn("Bağış", income_select)
        self.assertNotIn("Kira", income_select)

    def test_saving_choices_keeps_the_draft_and_posts_nothing(self):
        statement_import = self._draft()
        row = statement_import.rows.get(row_number=1)

        self.client.post(
            reverse("import_preview", args=[statement_import.pk]),
            {"action": "save", f"category_{row.pk}": self.expense_category.pk},
        )

        row.refresh_from_db()
        statement_import.refresh_from_db()
        self.assertEqual(row.category, self.expense_category)
        self.assertTrue(statement_import.is_draft)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_a_row_can_be_skipped(self):
        statement_import = self._draft()
        row = statement_import.rows.get(row_number=1)

        self.client.post(
            reverse("import_preview", args=[statement_import.pk]),
            {"action": "save", f"skip_{row.pk}": "on"},
        )

        row.refresh_from_db()
        self.assertTrue(row.is_skipped)

    # --- confirm ----------------------------------------------------------

    def test_confirming_creates_the_transactions(self):
        statement_import = self._draft()

        self.client.post(
            reverse("import_preview", args=[statement_import.pk]),
            self._confirm_payload(statement_import),
        )

        statement_import.refresh_from_db()
        self.assertEqual(statement_import.status, "confirmed")
        self.assertEqual(Transaction.objects.count(), 2)

    def test_imported_transactions_face_the_right_way(self):
        statement_import = self._draft()

        self.client.post(
            reverse("import_preview", args=[statement_import.pk]),
            self._confirm_payload(statement_import),
        )

        expense = Transaction.objects.get(transaction_type="expense")
        income = Transaction.objects.get(transaction_type="income")
        self.assertEqual(expense.source_account, self.account)
        self.assertIsNone(expense.target_account)
        self.assertEqual(income.target_account, self.account)
        self.assertIsNone(income.source_account)
        self.assertEqual(expense.amount, Decimal("1500.00"))

    def test_imported_transactions_are_recorded_in_the_audit_trail(self):
        statement_import = self._draft()

        self.client.post(
            reverse("import_preview", args=[statement_import.pk]),
            self._confirm_payload(statement_import),
        )

        logs = TransactionAuditLog.objects.filter(action="created")
        self.assertEqual(logs.count(), 2)
        self.assertIn("ekstre.csv", logs.first().reason)

    def test_confirming_without_categories_records_nothing(self):
        statement_import = self._draft()

        response = self.client.post(
            reverse("import_preview", args=[statement_import.pk]),
            {"action": "confirm"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "needing attention")
        self.assertEqual(Transaction.objects.count(), 0)
        statement_import.refresh_from_db()
        self.assertTrue(statement_import.is_draft)

    def test_skipped_rows_are_not_imported(self):
        statement_import = self._draft()
        skipped = statement_import.rows.get(row_number=1)
        payload = self._confirm_payload(statement_import)
        payload[f"skip_{skipped.pk}"] = "on"

        self.client.post(
            reverse("import_preview", args=[statement_import.pk]), payload
        )

        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(Transaction.objects.get().transaction_type, "income")

    def test_confirming_twice_does_not_double_post(self):
        statement_import = self._draft()
        payload = self._confirm_payload(statement_import)

        self.client.post(
            reverse("import_preview", args=[statement_import.pk]), payload
        )
        self.client.post(
            reverse("import_preview", args=[statement_import.pk]), payload
        )

        self.assertEqual(Transaction.objects.count(), 2)

    def test_rows_link_to_the_transaction_they_created(self):
        statement_import = self._draft()

        self.client.post(
            reverse("import_preview", args=[statement_import.pk]),
            self._confirm_payload(statement_import),
        )

        for row in statement_import.rows.all():
            self.assertIsNotNone(row.transaction_id)

    def test_a_failed_confirmation_leaves_no_partial_import(self):
        """Confirmation is atomic: one bad row must not leave the others
        posted, or the treasurer cannot tell what did and did not land.
        """
        statement_import = self._draft()
        broken = statement_import.rows.get(row_number=2)
        broken.date = None
        broken.save(update_fields=["date"])

        payload = self._confirm_payload(statement_import)
        with self.assertRaises(ValidationError):
            self.client.post(
                reverse("import_preview", args=[statement_import.pk]), payload
            )

        self.assertEqual(Transaction.objects.count(), 0)
        statement_import.refresh_from_db()
        self.assertTrue(statement_import.is_draft)

    # --- duplicates -------------------------------------------------------

    def test_a_line_matching_an_existing_transaction_is_flagged(self):
        self.create_transaction(
            transaction_type="expense",
            amount=Decimal("1500.00"),
            source_account=self.account,
            category=self.expense_category,
            created_by=self.treasurer,
            date="2026-09-01",
        )

        statement_import = self._draft()

        self.assertTrue(
            statement_import.rows.get(row_number=1).is_probable_duplicate
        )
        self.assertFalse(
            statement_import.rows.get(row_number=2).is_probable_duplicate
        )

    def test_the_duplicate_warning_is_shown_but_not_blocking(self):
        """Re-uploading is routine, so this warns and lets the reviewer judge
        rather than refusing the line outright.
        """
        self.create_transaction(
            transaction_type="expense",
            amount=Decimal("1500.00"),
            source_account=self.account,
            category=self.expense_category,
            created_by=self.treasurer,
            date="2026-09-01",
        )
        statement_import = self._draft()

        response = self.client.get(
            reverse("import_preview", args=[statement_import.pk])
        )

        self.assertContains(response, "already recorded")
        # Warned about, but not blocking: only a missing category or a parse
        # error stops confirmation.
        blocking_rows = [
            row for row, _reason in bank_ops.rows_needing_attention(
                statement_import
            )
        ]
        self.assertNotIn(
            statement_import.rows.get(row_number=1),
            [row for row in blocking_rows if row.is_probable_duplicate
             and not row.parse_error and row.category_id is not None],
        )

    # --- cancelling -------------------------------------------------------

    def test_a_draft_can_be_discarded(self):
        statement_import = self._draft()

        self.client.post(reverse("import_cancel", args=[statement_import.pk]))

        statement_import.refresh_from_db()
        self.assertEqual(statement_import.status, "cancelled")
        self.assertEqual(Transaction.objects.count(), 0)

    def test_a_confirmed_import_cannot_be_discarded(self):
        statement_import = self._draft()
        self.client.post(
            reverse("import_preview", args=[statement_import.pk]),
            self._confirm_payload(statement_import),
        )

        self.client.post(reverse("import_cancel", args=[statement_import.pk]))

        statement_import.refresh_from_db()
        self.assertEqual(statement_import.status, "confirmed")

    # --- permissions ------------------------------------------------------

    def test_data_entry_can_import(self):
        self.client.login(
            username=self.data_entry.username, password=self.password
        )

        response = self.client.get(reverse("import_new"))

        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_import(self):
        self.client.login(username=self.viewer.username, password=self.password)

        self.assertEqual(self.client.get(reverse("import_new")).status_code, 403)
        self.assertEqual(
            self.client.post(
                reverse("import_new"),
                {"account": self.account.pk, "statement_file": upload()},
            ).status_code,
            403,
        )
        self.assertEqual(BankStatementImport.objects.count(), 0)

    def test_viewer_can_still_see_the_import_history(self):
        self.client.login(username=self.viewer.username, password=self.password)

        self.assertEqual(self.client.get(reverse("import_list")).status_code, 200)

    def test_anonymous_user_is_redirected(self):
        self.client.logout()

        self.assertEqual(self.client.get(reverse("import_new")).status_code, 302)

    # --- sample file ------------------------------------------------------

    def test_sample_csv_downloads_and_parses(self):
        response = self.client.get(reverse("import_sample_csv"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])

        self._upload(text=response.content.decode("utf-8"))
        self.assertEqual(BankStatementImport.objects.count(), 1)
        self.assertEqual(
            BankStatementRow.objects.filter(parse_error="").count(), 3
        )
