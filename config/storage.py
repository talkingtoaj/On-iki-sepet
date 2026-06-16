import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

LOCAL_FILE_STORAGE_BACKEND = "django.core.files.storage.FileSystemStorage"
GCS_FILE_STORAGE_BACKEND = "storages.backends.gcloud.GoogleCloudStorage"


def get_file_storage_backend() -> str:
    return os.environ.get("DJANGO_FILE_STORAGE_BACKEND", "local").strip().lower()


def build_storages(*, media_root: Path, media_url: str) -> dict:
    backend = get_file_storage_backend()

    storages = {
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

    if backend == "local":
        storages["default"] = {
            "BACKEND": LOCAL_FILE_STORAGE_BACKEND,
        }
        return storages

    if backend == "gcs":
        bucket_name = os.environ.get("GCS_MEDIA_BUCKET_NAME", "").strip()
        if not bucket_name:
            raise ImproperlyConfigured(
                "GCS_MEDIA_BUCKET_NAME must be set when "
                "DJANGO_FILE_STORAGE_BACKEND=gcs."
            )

        gcs_options = {
            "bucket_name": bucket_name,
        }
        location = os.environ.get("GCS_MEDIA_LOCATION", "receipts").strip()
        if location:
            gcs_options["location"] = location

        storages["default"] = {
            "BACKEND": GCS_FILE_STORAGE_BACKEND,
            "OPTIONS": gcs_options,
        }
        return storages

    raise ImproperlyConfigured(
        f"Unsupported DJANGO_FILE_STORAGE_BACKEND value: {backend!r}. "
        "Use 'local' or 'gcs'."
    )


def get_debug_media_urlpatterns():
    from django.conf import settings
    from django.conf.urls.static import static

    if settings.DEBUG:
        return static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    return []
