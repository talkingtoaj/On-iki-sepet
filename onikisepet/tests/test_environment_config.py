"""Tests for the environment-driven settings helpers.

Settings used to hardcode DEBUG = True, an empty ALLOWED_HOSTS and a fallback
secret key, which meant a deployment could silently run in debug mode with a
known key. The rules now live in `config.env` as plain functions so they can be
tested directly instead of by reloading the settings module.
"""

from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from config import env as env_helpers


class AsBoolTests(TestCase):
    def test_truthy_values(self):
        for value in ["1", "true", "True", "TRUE", "yes", "on"]:
            self.assertTrue(env_helpers.as_bool(value), value)

    def test_falsy_values(self):
        for value in ["0", "false", "False", "no", "off", ""]:
            self.assertFalse(env_helpers.as_bool(value), value)

    def test_missing_value_uses_the_default(self):
        self.assertTrue(env_helpers.as_bool(None, default=True))
        self.assertFalse(env_helpers.as_bool(None, default=False))


class EnvironmentTests(TestCase):
    def test_default_environment_is_development(self):
        self.assertEqual(env_helpers.get_environment({}), "development")
        self.assertFalse(env_helpers.is_production({}))

    def test_production_must_be_declared_explicitly(self):
        self.assertTrue(env_helpers.is_production({"DJANGO_ENV": "production"}))

    def test_an_unknown_environment_is_rejected(self):
        """A typo like DJANGO_ENV=prod must fail loudly rather than quietly
        falling back to development settings on a live server.
        """
        with self.assertRaises(ImproperlyConfigured):
            env_helpers.get_environment({"DJANGO_ENV": "prod"})


class DebugTests(TestCase):
    def test_debug_is_on_by_default_in_development(self):
        self.assertTrue(env_helpers.get_debug({}))

    def test_debug_can_be_turned_off_in_development(self):
        self.assertFalse(env_helpers.get_debug({"DJANGO_DEBUG": "0"}))

    def test_production_is_never_in_debug_mode(self):
        """Even an explicit DJANGO_DEBUG=1 must not enable debug in
        production, where it would leak tracebacks and settings.
        """
        self.assertFalse(
            env_helpers.get_debug({"DJANGO_ENV": "production", "DJANGO_DEBUG": "1"})
        )


class SecretKeyTests(TestCase):
    def test_development_falls_back_to_a_clearly_marked_dev_key(self):
        key = env_helpers.get_secret_key({})

        self.assertIn("insecure", key)

    def test_production_without_a_secret_key_refuses_to_start(self):
        with self.assertRaises(ImproperlyConfigured):
            env_helpers.get_secret_key({"DJANGO_ENV": "production"})

    def test_production_rejects_the_development_fallback_key(self):
        with self.assertRaises(ImproperlyConfigured):
            env_helpers.get_secret_key(
                {
                    "DJANGO_ENV": "production",
                    "DJANGO_SECRET_KEY": env_helpers.DEV_SECRET_KEY,
                }
            )

    def test_production_rejects_a_key_with_too_few_distinct_characters(self):
        """A long but repetitive key passes a naive length test while being
        trivially guessable, and Django's own checklist rejects it too.
        """
        with self.assertRaises(ImproperlyConfigured):
            env_helpers.get_secret_key(
                {"DJANGO_ENV": "production", "DJANGO_SECRET_KEY": "ab" * 40}
            )

    def test_production_rejects_a_short_secret_key(self):
        with self.assertRaises(ImproperlyConfigured):
            env_helpers.get_secret_key(
                {"DJANGO_ENV": "production", "DJANGO_SECRET_KEY": "short"}
            )

    def test_production_accepts_a_strong_secret_key(self):
        strong = "Kd7-mZq2Wn5xRb8vTc3yLp6hGj9sFa4eQu1iOw0zXk"  # noqa: S105
        strong += "MnBvCxZ2"

        self.assertEqual(
            env_helpers.get_secret_key(
                {"DJANGO_ENV": "production", "DJANGO_SECRET_KEY": strong}
            ),
            strong,
        )


class AllowedHostsTests(TestCase):
    def test_development_defaults_to_localhost(self):
        hosts = env_helpers.get_allowed_hosts({})

        self.assertIn("localhost", hosts)
        self.assertIn("127.0.0.1", hosts)

    def test_hosts_are_split_and_trimmed(self):
        hosts = env_helpers.get_allowed_hosts(
            {"DJANGO_ALLOWED_HOSTS": " example.org , www.example.org "}
        )

        self.assertEqual(hosts, ["example.org", "www.example.org"])

    def test_production_without_allowed_hosts_refuses_to_start(self):
        with self.assertRaises(ImproperlyConfigured):
            env_helpers.get_allowed_hosts({"DJANGO_ENV": "production"})

    def test_csrf_trusted_origins_are_parsed(self):
        origins = env_helpers.get_csrf_trusted_origins(
            {"DJANGO_CSRF_TRUSTED_ORIGINS": "https://a.example, https://b.example"}
        )

        self.assertEqual(origins, ["https://a.example", "https://b.example"])


class DatabaseConfigTests(TestCase):
    base_dir = Path("/srv/app")

    def test_development_uses_sqlite(self):
        config = env_helpers.get_database_config({}, self.base_dir)

        self.assertIn("sqlite3", config["default"]["ENGINE"])
        self.assertEqual(config["default"]["NAME"], self.base_dir / "db.sqlite3")

    def test_postgres_is_used_when_configured(self):
        config = env_helpers.get_database_config(
            {
                "POSTGRES_DB": "onikisepet",
                "POSTGRES_USER": "app",
                "POSTGRES_PASSWORD": "secret",
                "POSTGRES_HOST": "10.0.0.5",
                "POSTGRES_PORT": "5432",
            },
            self.base_dir,
        )["default"]

        self.assertIn("postgresql", config["ENGINE"])
        self.assertEqual(config["NAME"], "onikisepet")
        self.assertEqual(config["USER"], "app")
        self.assertEqual(config["PASSWORD"], "secret")
        self.assertEqual(config["HOST"], "10.0.0.5")
        self.assertEqual(config["PORT"], "5432")

    def test_cloud_sql_socket_path_is_passed_through_as_the_host(self):
        """On Cloud Run the database is reached over a unix socket rather than
        a TCP host, so the socket directory has to survive unchanged.
        """
        socket = "/cloudsql/my-project:europe-west1:onikisepet"
        config = env_helpers.get_database_config(
            {"POSTGRES_DB": "onikisepet", "POSTGRES_HOST": socket},
            self.base_dir,
        )["default"]

        self.assertEqual(config["HOST"], socket)

    def test_production_requires_postgres(self):
        """SQLite on Cloud Run lives on an ephemeral disk, so the ledger would
        disappear on the next deploy.
        """
        with self.assertRaises(ImproperlyConfigured):
            env_helpers.get_database_config(
                {"DJANGO_ENV": "production"}, self.base_dir
            )


class SecuritySettingsTests(TestCase):
    def test_development_does_not_force_https(self):
        settings = env_helpers.get_security_settings({})

        self.assertFalse(settings["SECURE_SSL_REDIRECT"])
        self.assertFalse(settings["SESSION_COOKIE_SECURE"])
        self.assertEqual(settings["SECURE_HSTS_SECONDS"], 0)

    def test_production_enables_the_full_set(self):
        settings = env_helpers.get_security_settings({"DJANGO_ENV": "production"})

        self.assertTrue(settings["SECURE_SSL_REDIRECT"])
        self.assertTrue(settings["SESSION_COOKIE_SECURE"])
        self.assertTrue(settings["CSRF_COOKIE_SECURE"])
        self.assertTrue(settings["SECURE_HSTS_SECONDS"] >= 31536000)
        self.assertTrue(settings["SECURE_HSTS_INCLUDE_SUBDOMAINS"])
        self.assertTrue(settings["SECURE_CONTENT_TYPE_NOSNIFF"])
        self.assertEqual(settings["X_FRAME_OPTIONS"], "DENY")

    def test_production_trusts_the_proxy_forwarded_protocol_header(self):
        """Cloud Run terminates TLS upstream, so without this Django would see
        plain HTTP and redirect forever.
        """
        settings = env_helpers.get_security_settings({"DJANGO_ENV": "production"})

        self.assertEqual(
            settings["SECURE_PROXY_SSL_HEADER"], ("HTTP_X_FORWARDED_PROTO", "https")
        )


class DeploymentCheckTests(TestCase):
    """End-to-end proof that a production configuration passes Django's own
    deployment checklist. The unit tests above cover the rules; this catches a
    settings-wiring mistake that leaves a rule computed but never applied.
    """

    def _run_check(self, extra_env):
        import os
        import subprocess
        import sys

        base_dir = Path(__file__).resolve().parent.parent.parent
        environment = {**os.environ, **extra_env}
        environment.pop("DJANGO_SETTINGS_MODULE", None)

        return subprocess.run(
            [sys.executable, "manage.py", "check", "--deploy"],
            cwd=base_dir,
            env=environment,
            capture_output=True,
            text=True,
        )

    def _production_env(self, **overrides):
        environment = {
            "DJANGO_ENV": "production",
            "DJANGO_SECRET_KEY": "Kd7-mZq2Wn5xRb8vTc3yLp6hGj9sFa4eQu1iOw0zXkMnBvCxZ2",
            "DJANGO_ALLOWED_HOSTS": "onikisepet.example.org",
            "POSTGRES_DB": "onikisepet",
            "POSTGRES_USER": "app",
            "POSTGRES_PASSWORD": "secret",
            "POSTGRES_HOST": "/cloudsql/project:europe-west1:onikisepet",
        }
        environment.update(overrides)
        return environment

    def test_production_settings_pass_the_deployment_checklist(self):
        result = self._run_check(self._production_env())

        self.assertEqual(
            result.returncode,
            0,
            f"check --deploy failed:\n{result.stdout}\n{result.stderr}",
        )
        self.assertIn("no issues", result.stdout + result.stderr)

    def test_production_refuses_to_start_without_a_secret_key(self):
        result = self._run_check(self._production_env(DJANGO_SECRET_KEY=""))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY", result.stderr)

    def test_production_refuses_to_start_without_allowed_hosts(self):
        result = self._run_check(self._production_env(DJANGO_ALLOWED_HOSTS=""))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_ALLOWED_HOSTS", result.stderr)

    def test_production_refuses_to_start_on_sqlite(self):
        result = self._run_check(self._production_env(POSTGRES_DB=""))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("POSTGRES_DB", result.stderr)
