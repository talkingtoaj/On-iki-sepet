"""Reading bank statements into reviewable rows.

Bank exports differ in column naming, delimiter, date order and number format,
so the reader is deliberately tolerant about the shape of a file. It is strict
about meaning: a line it cannot understand is returned with an error attached
rather than skipped, because a dropped line is a transaction that quietly
never reaches the books.

Nothing here writes to the database. Parsing produces plain dictionaries; the
caller stores them as draft rows for a human to review.
"""

import csv
import io
from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from onikisepet.models import Transaction
from onikisepet.money_input import parse_amount

CSV_EXTENSIONS = (".csv", ".txt")
EXCEL_EXTENSIONS = (".xlsx", ".xlsm")
PDF_EXTENSIONS = (".pdf",)

# Column aliases, normalised: lowercased, stripped, Turkish dotted-I folded.
COLUMN_ALIASES = {
    "date": ["tarih", "islem tarihi", "işlem tarihi", "date", "value date"],
    "description": [
        "aciklama", "açıklama", "description", "detay", "explanation",
        "islem aciklamasi", "işlem açıklaması",
    ],
    "amount": ["tutar", "amount", "miktar", "islem tutari", "işlem tutarı"],
    "debit": ["borc", "borç", "debit", "cikan", "çıkan"],
    "credit": ["alacak", "credit", "giren"],
    "currency": ["para birimi", "currency", "doviz", "döviz", "pb"],
    "payee": ["alici", "alıcı", "payee", "karsi taraf", "karşı taraf"],
}

DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d.%m.%Y",
    "%d-%m-%Y",
    "%d/%m/%y",
    "%d.%m.%y",
    "%Y/%m/%d",
]

REQUIRED_EITHER = [("amount",), ("debit", "credit")]


class StatementFormatError(Exception):
    """The file as a whole cannot be read; no rows could be produced."""


def _normalise(value):
    text = str(value or "").strip().lower()
    # Turkish dotted capital İ lowercases to i̇ (i + combining dot), which
    # would not match a plain "i" in the alias table.
    return text.replace("̇", "").replace("ı", "i")


def map_headers(headers):
    """Column name -> index, for the columns we understand."""
    normalised = [_normalise(header) for header in headers]
    mapping = {}

    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            target = _normalise(alias)
            if target in normalised:
                mapping[field] = normalised.index(target)
                break

    if "date" not in mapping:
        raise StatementFormatError(
            _("No date column found. Expected one of: %(aliases)s.")
            % {"aliases": ", ".join(COLUMN_ALIASES["date"][:3])}
        )

    if not any(all(name in mapping for name in group) for group in REQUIRED_EITHER):
        raise StatementFormatError(
            _(
                "No amount column found. Expected an amount column, or "
                "separate debit and credit columns."
            )
        )

    return mapping


def parse_statement_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value or "").strip()
    if not text:
        raise ValueError(_("The date is missing."))

    for pattern in DATE_FORMATS:
        try:
            # A statement date is a calendar date with no time or zone, and
            # .date() discards the naive time part immediately.
            return datetime.strptime(text, pattern).date()  # noqa: DTZ007
        except ValueError:
            continue

    raise ValueError(_("“%(value)s” is not a date we recognise.") % {"value": text})


def _cell(values, mapping, field):
    index = mapping.get(field)
    if index is None or index >= len(values):
        return ""
    return values[index]


def _signed_amount(values, mapping):
    """A single signed figure, from either an amount or debit/credit columns."""
    if "amount" in mapping:
        raw = _cell(values, mapping, "amount")
        if str(raw).strip() == "":
            raise ValueError(_("The amount is missing."))
        return parse_amount(raw)

    debit = str(_cell(values, mapping, "debit")).strip()
    credit = str(_cell(values, mapping, "credit")).strip()

    if debit and credit:
        raise ValueError(
            _("This line has both a debit and a credit; only one is expected.")
        )
    if debit:
        return -abs(parse_amount(debit))
    if credit:
        return abs(parse_amount(credit))

    raise ValueError(_("The amount is missing."))


def classify(amount):
    """Money out of the account is an expense; money in is income."""
    if amount is None or amount == 0:
        return ""
    return (
        Transaction.TransactionType.EXPENSE
        if amount < 0
        else Transaction.TransactionType.INCOME
    )


def transaction_amount(amount):
    """Transactions store a positive amount; the type carries the direction."""
    return abs(amount)


def _parse_row(values, mapping, row_number, column_count=None):
    row = {
        "row_number": row_number,
        "date": None,
        "description": "",
        "payee": "",
        "amount": None,
        "currency": "",
        "transaction_type": "",
        "parse_error": "",
    }

    row["description"] = str(_cell(values, mapping, "description") or "").strip()
    row["payee"] = str(_cell(values, mapping, "payee") or "").strip()[:150]
    currency = str(_cell(values, mapping, "currency") or "").strip().upper()
    if currency in {"TL", "TRY"}:
        currency = "TRY"
    row["currency"] = currency if currency in {"TRY", "USD", "EUR"} else ""

    errors = []

    # More fields than the header means the delimiter or the quoting is wrong,
    # most often a Turkish amount like 1.500,00 sitting unquoted in a
    # comma-delimited file. Read on regardless and the amount silently loses
    # its kuruş, so this is refused instead.
    if column_count is not None and len(values) > column_count:
        extra = [str(v or "").strip() for v in values[column_count:]]
        if any(extra):
            row["parse_error"] = _(
                "This line has more columns than the header. The file's "
                "delimiter or quoting looks wrong, so the amount cannot be "
                "read safely."
            )
            return row

    try:
        row["date"] = parse_statement_date(_cell(values, mapping, "date"))
    except ValueError as exc:
        errors.append(str(exc))

    try:
        amount = _signed_amount(values, mapping)
        row["amount"] = amount
        row["transaction_type"] = classify(amount)
        if not row["transaction_type"]:
            errors.append(_("The amount is zero, so there is nothing to record."))
    except (ValueError, ValidationError) as exc:
        message = getattr(exc, "message", None) or getattr(exc, "messages", [None])[0]
        errors.append(str(message or exc))

    row["parse_error"] = " ".join(errors)
    return row


def _is_blank(values):
    return all(str(value or "").strip() == "" for value in values)


def _rows_from_table(table):
    if not table:
        raise StatementFormatError(_("The file is empty."))

    header, *body = table
    mapping = map_headers(header)

    rows, number = [], 0
    for values in body:
        if _is_blank(values):
            continue
        number += 1
        rows.append(_parse_row(values, mapping, number, column_count=len(header)))

    if not rows:
        raise StatementFormatError(_("The file has a header but no rows."))

    return rows


def _sniff_delimiter(text):
    """Turkish Excel exports use ';' because ',' is the decimal separator."""
    first_line = text.splitlines()[0] if text.splitlines() else ""
    return ";" if first_line.count(";") > first_line.count(",") else ","


def read_csv_rows(uploaded_file):
    uploaded_file.seek(0)
    raw = uploaded_file.read()
    if isinstance(raw, bytes):
        for encoding in ("utf-8-sig", "utf-8", "cp1254", "latin-1"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise StatementFormatError(_("The file's text encoding is unreadable."))
    else:
        text = raw

    if not text.strip():
        raise StatementFormatError(_("The file is empty."))

    reader = csv.reader(io.StringIO(text), delimiter=_sniff_delimiter(text))
    return _rows_from_table([row for row in reader])


def read_xlsx_rows(uploaded_file):
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise StatementFormatError(
            _("Excel support requires the openpyxl package.")
        ) from exc

    uploaded_file.seek(0)
    workbook = load_workbook(
        io.BytesIO(uploaded_file.read()), data_only=True, read_only=True
    )
    sheet = workbook.active
    table = [list(row) for row in sheet.iter_rows(values_only=True)]
    workbook.close()
    return _rows_from_table(table)


def read_pdf_rows(uploaded_file):
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise StatementFormatError(
            _("PDF support requires the pdfplumber package.")
        ) from exc

    uploaded_file.seek(0)
    table = []
    with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
        for page in pdf.pages:
            for extracted in page.extract_tables() or []:
                for values in extracted:
                    if values and not _is_blank(values):
                        table.append(list(values))

    if not table:
        raise StatementFormatError(
            _(
                "No table could be read from this PDF. Bank PDFs vary; "
                "exporting the statement as CSV or Excel is more reliable."
            )
        )

    return _rows_from_table(table)


def read_rows(uploaded_file):
    """Parsed rows from a statement file, chosen by extension."""
    name = (getattr(uploaded_file, "name", "") or "").lower()

    if name.endswith(CSV_EXTENSIONS):
        return read_csv_rows(uploaded_file)
    if name.endswith(EXCEL_EXTENSIONS):
        return read_xlsx_rows(uploaded_file)
    if name.endswith(PDF_EXTENSIONS):
        return read_pdf_rows(uploaded_file)

    raise StatementFormatError(
        _("Statements must be a CSV, Excel or PDF file.")
    )
