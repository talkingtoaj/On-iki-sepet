from pathlib import Path

from django.test import SimpleTestCase


class ProjectSetupTests(SimpleTestCase):
    def test_env_example_file_exists(self):
        env_example = Path(__file__).resolve().parents[2] / ".env.example"

        self.assertTrue(env_example.exists(), ".env.example must exist at project root")

    def test_env_example_documents_core_settings(self):
        env_example = Path(__file__).resolve().parents[2] / ".env.example"
        contents = env_example.read_text(encoding="utf-8")

        for key in (
            "DJANGO_SECRET_KEY",
            "DJANGO_FILE_STORAGE_BACKEND",
            "GCS_MEDIA_BUCKET_NAME",
            "DATABASE_URL",
        ):
            with self.subTest(key=key):
                self.assertIn(key, contents)

    def test_pyproject_declares_production_optional_dependencies(self):
        pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
        contents = pyproject.read_text(encoding="utf-8")

        self.assertIn("[project.optional-dependencies]", contents)
        self.assertIn("production =", contents)
        self.assertIn("django-storages", contents)
        self.assertIn("psycopg", contents)
