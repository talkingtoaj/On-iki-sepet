"""Turning a parsed statement into transactions, under review.

The shape of this is deliberate: uploading parses and stores draft rows and
writes nothing to the ledger. A human assigns categories, skips what should not
be imported, and only then confirms. Confirmation is atomic, so a statement
never lands half-imported.
"""

import csv
import io

from django.db import transaction as db_transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from onikisepet.models import BankStatementImport, BankStatementRow, Transaction
from onikisepet.usecases import audit, bank_import

SAMPLE_FILENAME = "ornek-ekstre.csv"


class ImportNotReady(Exception):
    """Confirmation was attempted while rows still need attention."""


def create_draft_import(*, account, uploaded_file, user):
    """Parse a statement into draft rows. Writes no transactions."""
    parsed = bank_import.read_rows(uploaded_file)

    with db_transaction.atomic():
        statement_import = BankStatementImport.objects.create(
            account=account,
            original_filename=(getattr(uploaded_file, "name", "") or "")[:255],
            uploaded_by=user,
        )

        for values in parsed:
            currency = values["currency"] or account.currency
            parse_error = values["parse_error"]

            # A statement line in another currency cannot belong to this
            # account, and guessing would post money to the wrong ledger.
            if not parse_error and currency != account.currency:
                parse_error = _(
                    "This line is in %(row)s but the account is %(account)s."
                ) % {"row": currency, "account": account.currency}

            BankStatementRow.objects.create(
                statement_import=statement_import,
                row_number=values["row_number"],
                date=values["date"],
                description=values["description"],
                payee=values["payee"],
                amount=(
                    bank_import.transaction_amount(values["amount"])
                    if values["amount"] is not None
                    else None
                ),
                currency=account.currency,
                transaction_type=values["transaction_type"],
                parse_error=parse_error,
            )

        flag_probable_duplicates(statement_import)

    return statement_import


def flag_probable_duplicates(statement_import):
    """Mark rows that look like a transaction already in the books.

    Statements get re-exported and re-uploaded, so the same line arriving
    twice is routine. This only warns; the reviewer decides.
    """
    account = statement_import.account
    flagged = 0

    for row in statement_import.rows.all():
        if row.parse_error or row.date is None or row.amount is None:
            continue

        side = (
            {"source_account": account}
            if row.transaction_type == Transaction.TransactionType.EXPENSE
            else {"target_account": account}
        )
        already_recorded = (
            Transaction.objects.active()
            .filter(date=row.date, amount=row.amount, **side)
            .exists()
        )

        if already_recorded != row.is_probable_duplicate:
            row.is_probable_duplicate = already_recorded
            row.save(update_fields=["is_probable_duplicate"])

        flagged += int(already_recorded)

    return flagged


def apply_row_choices(statement_import, *, categories, skipped):
    """Store the reviewer's per-row decisions.

    `categories` maps row id -> Category or None, `skipped` is the set of row
    ids to leave out.
    """
    for row in statement_import.rows.all():
        row.is_skipped = row.pk in skipped
        if row.pk in categories:
            row.category = categories[row.pk]
        row.save(update_fields=["is_skipped", "category"])


def rows_needing_attention(statement_import):
    """Rows that block confirmation, with the reason."""
    blocking = []

    for row in statement_import.rows.filter(is_skipped=False):
        if row.parse_error:
            blocking.append((row, row.parse_error))
        elif row.category_id is None:
            blocking.append((row, _("Choose a category, or skip this line.")))

    return blocking


def confirm_import(statement_import, user):
    """Create a transaction for every reviewed row, all or nothing."""
    if not statement_import.is_draft:
        raise ImportNotReady(
            _("This statement has already been %(status)s.")
            % {"status": statement_import.get_status_display().lower()}
        )

    blocking = rows_needing_attention(statement_import)
    if blocking:
        raise ImportNotReady(
            _("Lines still needing attention: %(count)s")
            % {"count": len(blocking)}
        )

    account = statement_import.account
    created = []

    with db_transaction.atomic():
        for row in statement_import.importable_rows():
            is_expense = (
                row.transaction_type == Transaction.TransactionType.EXPENSE
            )
            created_transaction = Transaction.objects.create(
                date=row.date,
                amount=row.amount,
                transaction_type=row.transaction_type,
                payee=row.payee,
                source_account=account if is_expense else None,
                target_account=None if is_expense else account,
                category=row.category,
                description=row.description,
                created_by=user,
            )
            audit.record_created(
                created_transaction,
                user,
                reason=_("Imported from %(file)s")
                % {"file": statement_import.original_filename},
            )
            row.transaction = created_transaction
            row.save(update_fields=["transaction"])
            created.append(created_transaction)

        statement_import.status = BankStatementImport.Status.CONFIRMED
        statement_import.confirmed_at = timezone.now()
        statement_import.save(update_fields=["status", "confirmed_at"])

    return created


def cancel_import(statement_import):
    if not statement_import.is_draft:
        raise ImportNotReady(_("Only a draft statement can be cancelled."))

    statement_import.status = BankStatementImport.Status.CANCELLED
    statement_import.save(update_fields=["status"])
    return statement_import


def build_sample_csv(account_name=None):
    """A correctly shaped example file, to save a round of failed uploads."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Tarih", "Açıklama", "Tutar", "Para Birimi"])
    writer.writerow(["01/09/2026", "Kira ödemesi", "-1.500,00", "TRY"])
    writer.writerow(["02/09/2026", "Bağış", "2.750,50", "TRY"])
    writer.writerow(["03/09/2026", "Elektrik faturası", "-430,25", "TRY"])
    return buffer.getvalue()
