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


@override_settings(LANGUAGE_CODE="en")
class CloudBuildPipelineTests(TestCase):
    """The deploy pipeline, checked for the properties that make it safe.

    The trigger on `main` is enabled, so this file is what runs against the
    church's live database. The ordering assertion below is the important one:
    it is the difference between a failed build and a half-migrated ledger.
    """

    def setUp(self):
        self.text = (ROOT / "cloudbuild.yaml").read_text()

    def test_cloudbuild_exists(self):
        self.assertTrue((ROOT / "cloudbuild.yaml").exists())

    def test_the_lineage_check_runs_before_the_migration(self):
        """Reversed, this pipeline would migrate a foreign database and only
        then notice. The check has to come first to be worth anything.
        """
        self.assertIn("check_database_lineage", self.text)
        self.assertLess(
            self.text.index("check_database_lineage"),
            self.text.index("- migrate"),
        )

    def test_the_pipeline_does_not_drop_the_database(self):
        """Wiping the database is a deliberate one-off in the runbook, never a
        step that runs on every push to main.
        """
        for destructive in ["databases delete", "flush", "sqlflush", "dbshell"]:
            self.assertNotIn(destructive, self.text)

    def test_the_pipeline_uses_this_lineage_settings_contract(self):
        """The collaborator's pipeline set config.production_settings and a
        single DATABASE_URL, neither of which exists here. The header comment
        names both to explain their absence, so assert on what the steps
        actually pass rather than on the file containing the words.
        """
        steps = self.text.split("steps:", 1)[1]

        self.assertNotIn("DJANGO_SETTINGS_MODULE", steps)
        self.assertNotIn("DATABASE_URL", steps)
        self.assertIn("DJANGO_ENV=production", steps)
        self.assertIn("POSTGRES_DB=", steps)

    def test_the_mail_substitutions_have_no_defaults(self):
        """An unset substitution fails the build while it is still parsing. A
        defaulted-to-empty mail host instead produces a container that boots,
        fails check --deploy and never serves.
        """
        declared = self.text.split("availableSecrets:")[0]

        for name in ["_EMAIL_HOST", "_EMAIL_USER", "_FROM_EMAIL"]:
            self.assertIn(f"${{{name}}}", self.text)
            self.assertNotIn(f"{name}:", declared)

    def test_migrations_do_not_run_in_the_deploy_step(self):
        """Migrations belong in their own pre-deploy step, not bundled into the
        gcloud run deploy call where a failure is harder to see.
        """
        deploy_step = self.text.split("- id: deploy")[1]

        self.assertNotIn("manage.py", deploy_step)
