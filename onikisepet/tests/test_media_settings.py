import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import clear_url_caches

from config.storage import (
    GCS_FILE_STORAGE_BACKEND,
    LOCAL_FILE_STORAGE_BACKEND,
    build_storages,
    get_debug_media_urlpatterns,
)
from onikisepet.models import Receipt

from .helpers import TransactionTestMixin


class MediaSettingsTests(TestCase):
    def test_media_root_points_to_project_media_directory(self):
        self.assertEqual(settings.MEDIA_ROOT, settings.BASE_DIR / "media")

    def test_media_url_is_configured(self):
        self.assertEqual(settings.MEDIA_URL, "/media/")

    def test_local_file_storage_uses_filesystem_backend(self):
        self.assertEqual(
            settings.STORAGES["default"]["BACKEND"],
            LOCAL_FILE_STORAGE_BACKEND,
        )

    def test_build_storages_uses_gcs_when_env_var_is_set(self):
        env = {
            "DJANGO_FILE_STORAGE_BACKEND": "gcs",
            "GCS_MEDIA_BUCKET_NAME": "oniki-sepet-media",
        }

        with patch.dict(os.environ, env, clear=False):
            storages = build_storages(
                media_root=Path("/tmp/media"),
                media_url="/media/",
            )

        self.assertEqual(storages["default"]["BACKEND"], GCS_FILE_STORAGE_BACKEND)
        self.assertEqual(
            storages["default"]["OPTIONS"]["bucket_name"],
            "oniki-sepet-media",
        )

    def test_build_storages_requires_bucket_name_for_gcs(self):
        env = {
            "DJANGO_FILE_STORAGE_BACKEND": "gcs",
            "GCS_MEDIA_BUCKET_NAME": "",
        }

        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(ImproperlyConfigured):
                build_storages(media_root=Path("/tmp/media"), media_url="/media/")

    def test_build_storages_rejects_unknown_backend(self):
        with patch.dict(os.environ, {"DJANGO_FILE_STORAGE_BACKEND": "s3"}, clear=False):
            with self.assertRaises(ImproperlyConfigured):
                build_storages(media_root=Path("/tmp/media"), media_url="/media/")


class MediaServingTests(TestCase):
    def test_debug_media_urlpatterns_are_registered(self):
        with override_settings(DEBUG=True, MEDIA_URL="/media/", MEDIA_ROOT="/tmp/media"):
            patterns = get_debug_media_urlpatterns()

        self.assertTrue(patterns)

    def test_media_urlpatterns_are_not_registered_when_debug_is_false(self):
        with override_settings(DEBUG=False, MEDIA_URL="/media/", MEDIA_ROOT="/tmp/media"):
            patterns = get_debug_media_urlpatterns()

        self.assertEqual(patterns, [])

    def test_media_file_is_served_in_debug_mode(self):
        import importlib

        import config.urls as config_urls

        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)

        receipts_dir = Path(media_root) / "receipts"
        receipts_dir.mkdir(parents=True)
        receipt_path = receipts_dir / "sample-receipt.pdf"
        receipt_path.write_bytes(b"receipt-bytes")

        with override_settings(
            DEBUG=True,
            MEDIA_URL="/media/",
            MEDIA_ROOT=media_root,
            ROOT_URLCONF="config.urls",
        ):
            importlib.reload(config_urls)
            clear_url_caches()
            response = self.client.get("/media/receipts/sample-receipt.pdf")
            importlib.reload(config_urls)
            clear_url_caches()

        self.assertEqual(response.status_code, 200)
        if hasattr(response, "streaming_content"):
            content = b"".join(response.streaming_content)
        else:
            content = response.content
        self.assertEqual(content, b"receipt-bytes")


class ReceiptFileStorageTests(TransactionTestMixin, TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        self.user = self.create_user("media_receipt_user", is_superuser=True)
        self.cash_account = self.create_account(
            name="Media Cash Account",
            account_type="cash",
            account_purpose="cash",
            currency="TRY",
        )
        self.expense_category = self.create_category(
            name="Media Expense",
            category_type="expense",
        )

    def _create_cash_expense_transaction(self):
        return self.get_transaction_model().objects.create(
            date="2026-06-13",
            transaction_type="expense",
            amount="50.00",
            currency="TRY",
            payee="Market",
            source_account=self.cash_account,
            category=self.expense_category,
            description="Cash expense with receipt",
            created_by=self.user,
        )

    def test_receipt_file_is_stored_under_media_root(self):
        receipt = Receipt.objects.create(
            transaction=self._create_cash_expense_transaction(),
            file=SimpleUploadedFile(
                "stored-receipt.pdf",
                b"stored receipt content",
                content_type="application/pdf",
            ),
            original_filename="stored-receipt.pdf",
            uploaded_by=self.user,
        )

        file_path = Path(self.media_root) / receipt.file.name

        self.assertTrue(receipt.file.name.startswith("receipts/"))
        self.assertTrue(file_path.is_file())
        self.assertEqual(file_path.read_bytes(), b"stored receipt content")

    def test_receipt_database_stores_file_reference_not_binary_content(self):
        receipt = Receipt.objects.create(
            transaction=self._create_cash_expense_transaction(),
            file=SimpleUploadedFile(
                "reference-receipt.jpg",
                b"binary should not live in db",
                content_type="image/jpeg",
            ),
            original_filename="reference-receipt.jpg",
            uploaded_by=self.user,
        )

        receipt_from_db = Receipt.objects.get(pk=receipt.pk)

        self.assertEqual(receipt_from_db.file.name, receipt.file.name)
        self.assertNotIn("binary should not live in db", str(receipt_from_db.file))
