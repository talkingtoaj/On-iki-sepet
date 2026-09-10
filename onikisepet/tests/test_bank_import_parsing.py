"""Reading bank statements.

Turkish bank exports vary in column naming, separator and number format, and a
statement is often re-exported and re-uploaded. Parsing therefore has to be
tolerant about shape and strict about meaning: a line it cannot read is kept
with its error rather than dropped, because a silently missing line is a
missing transaction nobody notices.
"""

import io
from datetime import date
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from onikisepet.usecases import bank_import


def csv_upload(text, name="ekstre.csv"):
    return SimpleUploadedFile(name, text.encode("utf-8"), content_type="text/csv")


@override_settings(LANGUAGE_CODE="en")
class HeaderMappingTests(TestCase):
    def test_turkish_headers_are_recognised(self):
        mapping = bank_import.map_headers(["Tarih", "Açıklama", "Tutar"])

        self.assertEqual(mapping["date"], 0)
        self.assertEqual(mapping["description"], 1)
        self.assertEqual(mapping["amount"], 2)

    def test_english_headers_are_recognised(self):
        mapping = bank_import.map_headers(["Date", "Description", "Amount"])

        self.assertEqual(mapping["date"], 0)
        self.assertEqual(mapping["amount"], 2)

    def test_header_matching_ignores_case_and_spacing(self):
        mapping = bank_import.map_headers(["  TARİH ", "aÇIklama", "TUTAR"])

        self.assertEqual(sorted(mapping), ["amount", "date", "description"])

    def test_separate_debit_and_credit_columns_are_recognised(self):
        mapping = bank_import.map_headers(["Tarih", "Açıklama", "Borç", "Alacak"])

        self.assertEqual(mapping["debit"], 2)
        self.assertEqual(mapping["credit"], 3)

    def test_optional_currency_column_is_recognised(self):
        mapping = bank_import.map_headers(["Tarih", "Tutar", "Para Birimi"])

        self.assertEqual(mapping["currency"], 2)

    def test_missing_required_columns_are_reported(self):
        with self.assertRaises(bank_import.StatementFormatError) as raised:
            bank_import.map_headers(["Tarih", "Açıklama"])

        self.assertIn("amount", str(raised.exception).lower())

    def test_a_file_with_no_recognisable_header_is_reported(self):
        with self.assertRaises(bank_import.StatementFormatError):
            bank_import.map_headers(["foo", "bar", "baz"])


@override_settings(LANGUAGE_CODE="en")
class CsvParsingTests(TestCase):
    def test_a_simple_statement_parses(self):
        rows = bank_import.read_rows(
            csv_upload(
                "Tarih,Açıklama,Tutar\n"
                '01/09/2026,Kira ödemesi,"-1.500,00"\n'
                '02/09/2026,Bağış,"2.750,50"\n'
            )
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["date"], date(2026, 9, 1))
        self.assertEqual(rows[0]["amount"], Decimal("-1500.00"))
        self.assertEqual(rows[0]["description"], "Kira ödemesi")
        self.assertEqual(rows[1]["amount"], Decimal("2750.50"))

    def test_semicolon_delimited_files_parse(self):
        """Turkish Excel exports use ';' because ',' is the decimal mark."""
        rows = bank_import.read_rows(
            csv_upload(
                "Tarih;Açıklama;Tutar\n01/09/2026;Kira;-1.500,00\n"
            )
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["amount"], Decimal("-1500.00"))

    def test_iso_dates_parse(self):
        rows = bank_import.read_rows(
            csv_upload("Tarih,Açıklama,Tutar\n2026-09-01,Kira,-100.00\n")
        )

        self.assertEqual(rows[0]["date"], date(2026, 9, 1))
    def test_dotted_dates_parse(self):
        rows = bank_import.read_rows(
            csv_upload("Tarih,Açıklama,Tutar\n01.09.2026,Kira,-100.00\n")
        )

        self.assertEqual(rows[0]["date"], date(2026, 9, 1))

    def test_debit_and_credit_columns_become_a_signed_amount(self):
        rows = bank_import.read_rows(
            csv_upload(
                'Tarih,Açıklama,Borç,Alacak\n'
                '01/09/2026,Kira,"1.500,00",\n'
                '02/09/2026,Bağış,,"2.750,50"\n'
            )
        )

        self.assertEqual(rows[0]["amount"], Decimal("-1500.00"))
        self.assertEqual(rows[1]["amount"], Decimal("2750.50"))

    def test_blank_lines_are_ignored(self):
        rows = bank_import.read_rows(
            csv_upload("Tarih,Açıklama,Tutar\n\n01/09/2026,Kira,-100.00\n\n")
        )

        self.assertEqual(len(rows), 1)

    def test_an_unreadable_line_is_kept_with_its_error(self):
        """A dropped line is a missing transaction, so it is surfaced instead."""
        rows = bank_import.read_rows(
            csv_upload(
                "Tarih,Açıklama,Tutar\n"
                "01/09/2026,Kira,-100.00\n"
                "not-a-date,Broken,abc\n"
            )
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["parse_error"], "" if False else rows[1]["parse_error"])
        self.assertTrue(rows[1]["parse_error"])
        self.assertIsNone(rows[1]["amount"])

    def test_an_unquoted_turkish_amount_is_refused_not_mis_read(self):
        """A comma-delimited file cannot hold an unquoted 2.750,50.

        Splitting it across columns would read the amount as 2750 and lose the
        kuruş silently, which is far worse than refusing the line.
        """
        rows = bank_import.read_rows(
            csv_upload("Tarih,Açıklama,Tutar\n02/09/2026,Bağış,2.750,50\n")
        )

        self.assertTrue(rows[0]["parse_error"])
        self.assertIsNone(rows[0]["amount"])
        self.assertIn("delimiter", rows[0]["parse_error"].lower())

    def test_row_numbers_follow_the_file(self):
        rows = bank_import.read_rows(
            csv_upload(
                "Tarih,Açıklama,Tutar\n01/09/2026,A,-1.00\n02/09/2026,B,-2.00\n"
            )
        )

        self.assertEqual([r["row_number"] for r in rows], [1, 2])

    def test_currency_column_is_used_when_present(self):
        rows = bank_import.read_rows(
            csv_upload("Tarih,Tutar,Para Birimi\n01/09/2026,-100.00,USD\n")
        )

        self.assertEqual(rows[0]["currency"], "USD")

    def test_an_empty_file_is_reported(self):
        with self.assertRaises(bank_import.StatementFormatError):
            bank_import.read_rows(csv_upload(""))

    def test_an_unsupported_extension_is_reported(self):
        with self.assertRaises(bank_import.StatementFormatError):
            bank_import.read_rows(csv_upload("Tarih,Tutar\n", name="ekstre.docx"))


@override_settings(LANGUAGE_CODE="en")
class ClassificationTests(TestCase):
    def test_a_negative_amount_is_an_expense(self):
        self.assertEqual(bank_import.classify(Decimal("-100.00")), "expense")

    def test_a_positive_amount_is_income(self):
        self.assertEqual(bank_import.classify(Decimal("100.00")), "income")

    def test_zero_has_no_classification(self):
        self.assertEqual(bank_import.classify(Decimal("0.00")), "")

    def test_absolute_amount_is_used_for_the_transaction(self):
        """Transactions store a positive amount; direction is the type."""
        self.assertEqual(
            bank_import.transaction_amount(Decimal("-100.00")), Decimal("100.00")
        )


@override_settings(LANGUAGE_CODE="en")
class XlsxParsingTests(TestCase):
    def _xlsx(self, rows, name="ekstre.xlsx"):
        from openpyxl import Workbook

        book = Workbook()
        sheet = book.active
        for row in rows:
            sheet.append(row)
        buffer = io.BytesIO()
        book.save(buffer)
        return SimpleUploadedFile(
            name,
            buffer.getvalue(),
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )

    def test_an_excel_statement_parses(self):
        upload = self._xlsx(
            [
                ["Tarih", "Açıklama", "Tutar"],
                ["01/09/2026", "Kira", "-1.500,00"],
                ["02/09/2026", "Bağış", "2.750,50"],
            ]
        )

        rows = bank_import.read_rows(upload)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["amount"], Decimal("-1500.00"))
        self.assertEqual(rows[1]["description"], "Bağış")

    def test_native_excel_dates_and_numbers_parse(self):
        upload = self._xlsx(
            [
                ["Tarih", "Açıklama", "Tutar"],
                [date(2026, 9, 1), "Kira", -1500.00],
            ]
        )

        rows = bank_import.read_rows(upload)

        self.assertEqual(rows[0]["date"], date(2026, 9, 1))
        self.assertEqual(rows[0]["amount"], Decimal("-1500.00"))
