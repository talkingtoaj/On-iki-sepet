from pathlib import Path

from django.db import connection
from django.test import Client, SimpleTestCase, TestCase, override_settings
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class DockerfileDeploymentTests(SimpleTestCase):
    def test_dockerfile_sets_production_settings_module(self):
        dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn(
            "DJANGO_SETTINGS_MODULE=config.production_settings",
            dockerfile,
        )

    def test_dockerfile_uses_entrypoint_for_migrations(self):
        dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
        entrypoint = (PROJECT_ROOT / "docker" / "entrypoint.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("entrypoint", dockerfile.lower())
        self.assertIn("migrate", entrypoint)
        self.assertIn("--noinput", entrypoint)

    def test_dockerfile_installs_production_optional_dependencies(self):
        dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertRegex(dockerfile, r'pip install.*"\.\[production\]"')


class EntrypointScriptTests(SimpleTestCase):
    def test_entrypoint_is_executable_shell_script(self):
        entrypoint_path = PROJECT_ROOT / "docker" / "entrypoint.sh"

        self.assertTrue(entrypoint_path.is_file())
        contents = entrypoint_path.read_text(encoding="utf-8")
        self.assertTrue(contents.startswith("#!/"))
        self.assertIn('exec "$@"', contents)


class HealthCheckTests(TestCase):
    def test_health_endpoint_returns_ok_when_database_is_available(self):
        response = Client().get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_endpoint_returns_service_unavailable_when_database_fails(self):
        with patch.object(connection, "ensure_connection", side_effect=Exception("db down")):
            response = Client().get("/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_health_endpoint_does_not_require_authentication(self):
        response = Client().get("/health/")

        self.assertNotEqual(response.status_code, 302)
        self.assertNotIn("/accounts/login/", response.get("Location", ""))


class CiCdWorkflowTests(SimpleTestCase):
    def test_ci_workflow_exists_and_runs_tests(self):
        workflow = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"

        self.assertTrue(workflow.is_file())
        contents = workflow.read_text(encoding="utf-8")
        self.assertIn("manage.py test", contents)
        self.assertIn("onikisepet", contents)

    def test_deploy_workflow_exists_for_gcp(self):
        workflow = PROJECT_ROOT / ".github" / "workflows" / "deploy-gcp.yml"

        self.assertTrue(workflow.is_file())
        contents = workflow.read_text(encoding="utf-8")
        for fragment in (
            "Artifact Registry",
            "Cloud Run",
            "DATABASE_URL",
            "GCS_MEDIA_BUCKET_NAME",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, contents)


class OperationsDocsTests(SimpleTestCase):
    def test_runbook_documents_health_backup_and_incident_response(self):
        runbook = PROJECT_ROOT / "docs" / "deployment" / "runbook.md"

        self.assertTrue(runbook.is_file())
        contents = runbook.read_text(encoding="utf-8").lower()
        for topic in ("health", "backup", "restore", "cloud sql", "cloud run"):
            with self.subTest(topic=topic):
                self.assertIn(topic, contents)

    def test_backup_script_uses_database_url(self):
        script = PROJECT_ROOT / "scripts" / "backup_database.sh"

        self.assertTrue(script.is_file())
        contents = script.read_text(encoding="utf-8")
        self.assertIn("DATABASE_URL", contents)
        self.assertIn("pg_dump", contents)
