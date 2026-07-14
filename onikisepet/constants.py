from decimal import Decimal

ALLOWED_RECEIPT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

RECEIPT_FILE_ACCEPT = "image/*,.pdf,application/pdf"

RECEIPT_EXTENSION_TO_FILE_TYPE = {
    ".pdf": "pdf",
    ".jpg": "jpg",
    ".jpeg": "jpg",
    ".png": "png",
}

ALLOWED_BANK_IMPORT_EXTENSIONS = {".csv", ".xlsx", ".pdf"}

BANK_IMPORT_REQUIRED_COLUMNS = {
    "date",
    "description",
    "amount",
    "currency",
    "account",
}

MONEY_FIELD_KWARGS = {
    "max_digits": 12,
    "decimal_places": 2,
}

POSITIVE_MONEY_FIELD_KWARGS = {
    **MONEY_FIELD_KWARGS,
    "min_value": Decimal("0.01"),
}