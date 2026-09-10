"""Validation for uploaded receipt files.

Receipts are financial evidence that gets stored and served back to users, so
two things matter: only the declared formats are accepted, and the file's
declared extension is checked against its actual content. A renamed executable
or an SVG with script in it must not get through on the strength of its name.
"""

import contextlib

from django.core.exceptions import ValidationError

MAX_RECEIPT_SIZE_BYTES = 10 * 1024 * 1024

ALLOWED_RECEIPT_EXTENSIONS = ("jpg", "jpeg", "png", "pdf")

# Leading bytes that identify each accepted format.
MAGIC_PREFIXES_BY_EXTENSION = {
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "pdf": (b"%PDF-",),
}

HEADER_LENGTH = 8


def _extension_of(uploaded_file):
    name = getattr(uploaded_file, "name", "") or ""
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[-1].lower()


def _read_header(uploaded_file):
    """First few bytes of the file, leaving the read position where it was."""
    try:
        position = uploaded_file.tell()
    except (AttributeError, ValueError, OSError):
        position = 0

    try:
        uploaded_file.seek(0)
        header = uploaded_file.read(HEADER_LENGTH)
    except (AttributeError, ValueError, OSError):
        return b""
    finally:
        with contextlib.suppress(AttributeError, ValueError, OSError):
            uploaded_file.seek(position)

    return header or b""


def validate_receipt_file(uploaded_file):
    extension = _extension_of(uploaded_file)

    if extension not in ALLOWED_RECEIPT_EXTENSIONS:
        raise ValidationError(
            "Receipts must be a %(allowed)s file.",
            code="invalid_receipt_extension",
            params={"allowed": ", ".join(ALLOWED_RECEIPT_EXTENSIONS).upper()},
        )

    size = getattr(uploaded_file, "size", None)
    if size is not None and size > MAX_RECEIPT_SIZE_BYTES:
        raise ValidationError(
            "Receipts must be %(limit)s MB or smaller.",
            code="receipt_too_large",
            params={"limit": MAX_RECEIPT_SIZE_BYTES // (1024 * 1024)},
        )

    header = _read_header(uploaded_file)
    expected_prefixes = MAGIC_PREFIXES_BY_EXTENSION[extension]

    if not any(header.startswith(prefix) for prefix in expected_prefixes):
        raise ValidationError(
            "This file is not a valid %(extension)s file. Its contents do not "
            "match its extension.",
            code="receipt_content_mismatch",
            params={"extension": extension.upper()},
        )
