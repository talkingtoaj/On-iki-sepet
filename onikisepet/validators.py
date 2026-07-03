from pathlib import Path
from django.core.exceptions import ValidationError

from .constants import (
    ALLOWED_BANK_IMPORT_EXTENSIONS,
    ALLOWED_RECEIPT_EXTENSIONS,
    RECEIPT_EXTENSION_TO_FILE_TYPE,
)
from onikisepet import messages as msg


def validate_receipt_file_extension(uploaded_file):
    extension = Path(uploaded_file.name).suffix.lower()

    if extension not in ALLOWED_RECEIPT_EXTENSIONS:
        raise ValidationError(msg.UNSUPPORTED_RECEIPT_FILE)


def derive_receipt_file_type(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    file_type = RECEIPT_EXTENSION_TO_FILE_TYPE.get(extension)
    if file_type is None:
        raise ValidationError(msg.UNSUPPORTED_RECEIPT_FILE)
    return file_type


def validate_bank_import_file_extension(uploaded_file):
    extension = Path(uploaded_file.name).suffix.lower()

    if extension not in ALLOWED_BANK_IMPORT_EXTENSIONS:
        raise ValidationError(msg.UNSUPPORTED_BANK_IMPORT_FILE)
