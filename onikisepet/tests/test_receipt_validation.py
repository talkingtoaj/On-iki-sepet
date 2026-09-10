import tempfile
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from onikisepet.validators import (
    MAX_RECEIPT_SIZE_BYTES,
    validate_receipt_file,
)

from .helpers import (
    JPEG_BYTES,
    PDF_BYTES,
    PNG_BYTES,
    ReceiptFileTestMixin,
    TransactionTestMixin,
)


@override_settings(LANGUAGE_CODE="en")
class ReceiptFileValidatorTests(ReceiptFileTestMixin, TestCase):
    """Receipts carry sensitive financial information and are served back to
    users, so the upload field must accept only the declared formats and must
    not trust the file extension on its own.
    """

    def test_accepts_a_jpeg(self):
        validate_receipt_file(self.make_receipt_file("receipt.jpg"))

    def test_accepts_a_jpeg_with_the_jpeg_extension(self):
        validate_receipt_file(self.make_receipt_file("receipt.jpeg"))

    def test_accepts_a_png(self):
        validate_receipt_file(
            self.make_receipt_file("receipt.png", content_type="image/png")
        )

    def test_accepts_a_pdf(self):
        validate_receipt_file(
            self.make_receipt_file("receipt.pdf", content_type="application/pdf")
        )

    def test_rejects_an_executable(self):
        with self.assertRaises(ValidationError):
            validate_receipt_file(
                self.make_receipt_file("payload.exe", content=b"MZ\x90\x00")
            )

    def test_rejects_an_svg_which_browsers_can_execute_as_markup(self):
        with self.assertRaises(ValidationError):
            validate_receipt_file(
                self.make_receipt_file("receipt.svg", content=b"<svg></svg>")
            )

    def test_rejects_html(self):
        with self.assertRaises(ValidationError):
            validate_receipt_file(
                self.make_receipt_file("receipt.html", content=b"<html></html>")
            )

    def test_rejects_a_file_with_no_extension(self):
        with self.assertRaises(ValidationError):
            validate_receipt_file(self.make_receipt_file("receipt", content=JPEG_BYTES))

    def test_rejects_an_executable_renamed_to_look_like_a_jpeg(self):
        """The extension alone is not evidence. A renamed binary must fail."""
        with self.assertRaises(ValidationError):
            validate_receipt_file(
                self.make_receipt_file("receipt.jpg", content=b"MZ\x90\x00" * 8)
            )

    def test_rejects_a_pdf_renamed_to_png(self):
        with self.assertRaises(ValidationError):
            validate_receipt_file(
                self.make_receipt_file("receipt.png", content=PDF_BYTES)
            )

    def test_accepts_a_png_whose_content_really_is_a_png(self):
        validate_receipt_file(self.make_receipt_file("receipt.png", content=PNG_BYTES))

    def test_rejects_a_file_over_the_size_limit(self):
        oversized = JPEG_BYTES + b"\x00" * MAX_RECEIPT_SIZE_BYTES

        with self.assertRaises(ValidationError):
            validate_receipt_file(
                self.make_receipt_file("receipt.jpg", content=oversized)
            )

    def test_accepts_a_file_just_under_the_size_limit(self):
        padding = MAX_RECEIPT_SIZE_BYTES - len(JPEG_BYTES)
        just_under = JPEG_BYTES + b"\x00" * (padding - 1)

        validate_receipt_file(
            self.make_receipt_file("receipt.jpg", content=just_under)
        )

    def test_extension_check_is_case_insensitive(self):
        validate_receipt_file(self.make_receipt_file("RECEIPT.JPG"))


@override_settings(LANGUAGE_CODE="en")
@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ReceiptModelValidationTests(
    ReceiptFileTestMixin, TransactionTestMixin, TestCase
):
    """Validation has to sit on the model field, not only the form, so that
    admin and shell writes are covered too.
    """

    def setUp(self):
        self.user = self.create_user("receipt_validation_user", is_superuser=True)
        self.cash_account = self.create_account(
            name="Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.expense_category = self.create_category(
            name="Supplies",
            category_type="expense",
        )
        self.transaction = self.create_transaction(
            transaction_type="expense",
            amount=Decimal("125.00"),
            source_account=self.cash_account,
            category=self.expense_category,
            created_by=self.user,
        )

    def _create_receipt(self, uploaded_file):
        from onikisepet.models import Receipt

        return Receipt.objects.create(
            transaction=self.transaction,
            file=uploaded_file,
            original_filename=uploaded_file.name,
            uploaded_by=self.user,
        )

    def test_valid_receipt_is_stored(self):
        receipt = self._create_receipt(self.make_receipt_file("receipt.jpg"))

        self.assertIsNotNone(receipt.pk)

    def test_model_rejects_a_disallowed_extension(self):
        with self.assertRaises(ValidationError):
            self._create_receipt(
                self.make_receipt_file("payload.exe", content=b"MZ\x90\x00")
            )

    def test_model_rejects_content_that_does_not_match_the_extension(self):
        with self.assertRaises(ValidationError):
            self._create_receipt(
                self.make_receipt_file("receipt.jpg", content=b"not an image at all")
            )
