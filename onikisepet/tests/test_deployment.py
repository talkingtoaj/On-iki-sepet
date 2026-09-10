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

    def test_the_deploy_declares_a_mail_backend_explicitly(self):
        """There is no mail infrastructure yet, and config/env.py refuses to
        import settings in production with the SMTP backend and no host. The
        deploy has to name a backend, or the container boots, fails the
        entrypoint's check --deploy, and never serves.
        """
        deploy_step = self.text.split("- id: deploy")[1]

        self.assertIn("DJANGO_EMAIL_BACKEND=${_EMAIL_BACKEND}", deploy_step)

    def test_the_default_mail_backend_does_not_need_a_host(self):
        """Whatever the default is, it must not be the SMTP backend: that is
        the one combination config/env.py rejects without a host.
        """
        declared = self.text.split("availableSecrets:")[0]

        self.assertIn("_EMAIL_BACKEND:", declared)
        self.assertNotIn("_EMAIL_BACKEND: django.core.mail.backends.smtp", declared)

    def _steps_before_deploy(self):
        """Each `- id:` block ahead of the deploy step, as (id, body) pairs."""
        before_deploy = self.text.split("- id: deploy")[0]
        blocks = before_deploy.split("- id: ")[1:]

        return [(block.split("\n", 1)[0].strip(), block) for block in blocks]

    def test_every_build_step_that_runs_django_declares_a_mail_backend(self):
        """These steps run with DJANGO_ENV=production, where config/env.py
        refuses to import settings under the SMTP backend with no host. Counting
        occurrences would rot as steps are added, so check each step instead.
        """
        checked = []

        for step_id, body in self._steps_before_deploy():
            if "manage.py" not in body:
                continue
            checked.append(step_id)
            self.assertIn(
                "DJANGO_EMAIL_BACKEND=django.core.mail.backends.dummy.EmailBackend",
                body,
                f"step {step_id} runs Django without declaring a mail backend",
            )

        # Guard the guard: if the parsing above ever matches nothing, the loop
        # would pass while asserting nothing at all.
        self.assertGreaterEqual(len(checked), 2)

    def test_seeding_runs_after_the_migration(self):
        """Seeding writes rows, so it needs the schema to exist first."""
        self.assertLess(self.text.index("- id: migrate"), self.text.index("- id: seed-roles"))
        self.assertLess(
            self.text.index("- id: seed-roles"), self.text.index("- id: seed-kut-data")
        )

    def test_seeding_runs_before_the_service_goes_live(self):
        """Deploying first would put a service in front of a database with no
        roles and no chart of accounts.
        """
        self.assertLess(
            self.text.index("- id: seed-kut-data"), self.text.index("- id: deploy")
        )

    def test_only_idempotent_commands_run_on_every_deploy(self):
        """This pipeline runs on every push to main. seed_roles and
        seed_kut_data are written to be repeatable; createsuperuser is not, and
        loaddata would trample edited rows.
        """
        for step_id, body in self._steps_before_deploy():
            for unsafe in ["createsuperuser", "loaddata", "flush"]:
                self.assertNotIn(unsafe, body, f"{unsafe} must not run in {step_id}")

    def test_migrations_do_not_run_in_the_deploy_step(self):
        """Migrations belong in their own pre-deploy step, not bundled into the
        gcloud run deploy call where a failure is harder to see.
        """
        deploy_step = self.text.split("- id: deploy")[1]

        self.assertNotIn("manage.py", deploy_step)
