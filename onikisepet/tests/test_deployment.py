"""Deployment artefacts.

These are cheap structural checks. They will not prove a deploy works, but
they do catch the failures that are otherwise only discovered in the middle of
one: a Dockerfile that runs migrations at start-up, or an entrypoint that no
longer verifies the settings.
"""

import pathlib

from django.test import TestCase, override_settings

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


@override_settings(LANGUAGE_CODE="en")
class DeploymentArtefactTests(TestCase):
    def test_dockerfile_exists(self):
        self.assertTrue((ROOT / "Dockerfile").exists())

    def test_entrypoint_exists_and_is_executable(self):
        entrypoint = ROOT / "docker" / "entrypoint.sh"

        self.assertTrue(entrypoint.exists())
        self.assertTrue(entrypoint.stat().st_mode & 0o111)

    def test_the_container_does_not_migrate_on_start_up(self):
        """Cloud Run cold-starts several containers at once, which would race
        the same migration. Migrations belong in a pre-deploy step.
        """
        entrypoint = (ROOT / "docker" / "entrypoint.sh").read_text()

        self.assertNotIn("manage.py migrate", entrypoint)

    def test_the_entrypoint_verifies_the_settings_before_serving(self):
        entrypoint = (ROOT / "docker" / "entrypoint.sh").read_text()

        self.assertIn("check --deploy", entrypoint)

    def test_the_build_compiles_translations(self):
        """Without this the Turkish catalogue is absent in the image and every
        string silently falls back to English.
        """
        dockerfile = (ROOT / "Dockerfile").read_text()

        self.assertIn("compilemessages", dockerfile)

    def test_the_build_collects_static_files(self):
        dockerfile = (ROOT / "Dockerfile").read_text()

        self.assertIn("collectstatic", dockerfile)

    def test_the_container_runs_unprivileged(self):
        dockerfile = (ROOT / "Dockerfile").read_text()

        self.assertIn("USER appuser", dockerfile)

    def test_the_container_uses_the_locked_dependency_set(self):
        dockerfile = (ROOT / "Dockerfile").read_text()

        self.assertIn("uv sync --locked", dockerfile)

    def test_the_build_time_secret_is_not_a_plausible_real_one(self):
        """A placeholder that looked real could be mistaken for the actual
        key and copied into a deployment.
        """
        dockerfile = (ROOT / "Dockerfile").read_text()

        self.assertIn("build-time-only", dockerfile)

    def test_backup_script_exists_and_is_executable(self):
        script = ROOT / "scripts" / "backup_database.sh"

        self.assertTrue(script.exists())
        self.assertTrue(script.stat().st_mode & 0o111)

    def test_runbook_exists_and_covers_the_migration_hazard(self):
        runbook = ROOT / "docs" / "deployment" / "runbook.md"

        self.assertTrue(runbook.exists())
        text = runbook.read_text()
        self.assertIn("never from the container entrypoint", text)
        self.assertIn("seed_roles", text)
