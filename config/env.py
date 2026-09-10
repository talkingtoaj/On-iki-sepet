"""Environment-driven configuration rules.

These are plain functions taking an environment mapping so they can be tested
directly. The guiding rule is that production must be declared explicitly, and
declaring it enforces everything a live church-finance deployment needs: a real
secret key, a real host list, PostgreSQL, HTTPS, and debug off.
"""

from django.core.exceptions import ImproperlyConfigured

DEVELOPMENT = "development"
PRODUCTION = "production"
VALID_ENVIRONMENTS = (DEVELOPMENT, PRODUCTION)

DEV_SECRET_KEY = "dev-only-insecure-key-not-for-production"
MIN_SECRET_KEY_LENGTH = 50
MIN_SECRET_KEY_UNIQUE_CHARACTERS = 5

ONE_YEAR_IN_SECONDS = 31536000

TRUTHY = {"1", "true", "yes", "on"}
FALSY = {"0", "false", "no", "off", ""}


def as_bool(value, default=False):
    if value is None:
        return default

    normalised = str(value).strip().lower()
    if normalised in TRUTHY:
        return True
    if normalised in FALSY:
        return False

    raise ImproperlyConfigured(f"Expected a boolean value, got {value!r}.")


def get_environment(env):
    environment = env.get("DJANGO_ENV", DEVELOPMENT).strip().lower()

    if environment not in VALID_ENVIRONMENTS:
        raise ImproperlyConfigured(
            f"DJANGO_ENV must be one of {', '.join(VALID_ENVIRONMENTS)}, "
            f"got {environment!r}."
        )

    return environment


def is_production(env):
    return get_environment(env) == PRODUCTION


def get_debug(env):
    """Debug is never on in production, whatever the environment says."""
    if is_production(env):
        return False

    return as_bool(env.get("DJANGO_DEBUG"), default=True)


def get_secret_key(env):
    secret_key = env.get("DJANGO_SECRET_KEY", "").strip()

    if not is_production(env):
        return secret_key or DEV_SECRET_KEY

    if not secret_key:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set when DJANGO_ENV=production."
        )
    if secret_key == DEV_SECRET_KEY:
        raise ImproperlyConfigured(
            "The development secret key must not be used in production."
        )
    if len(secret_key) < MIN_SECRET_KEY_LENGTH:
        raise ImproperlyConfigured(
            f"DJANGO_SECRET_KEY must be at least {MIN_SECRET_KEY_LENGTH} "
            "characters in production."
        )
    if len(set(secret_key)) < MIN_SECRET_KEY_UNIQUE_CHARACTERS:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must use at least "
            f"{MIN_SECRET_KEY_UNIQUE_CHARACTERS} distinct characters in "
            "production. Generate one with "
            "`python -c 'import secrets; print(secrets.token_urlsafe(64))'`."
        )

    return secret_key


def _split_list(raw):
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


def get_allowed_hosts(env):
    hosts = _split_list(env.get("DJANGO_ALLOWED_HOSTS"))

    if hosts:
        return hosts

    if is_production(env):
        raise ImproperlyConfigured(
            "DJANGO_ALLOWED_HOSTS must be set when DJANGO_ENV=production."
        )

    return ["localhost", "127.0.0.1", "[::1]", "testserver"]


def get_csrf_trusted_origins(env):
    return _split_list(env.get("DJANGO_CSRF_TRUSTED_ORIGINS"))


def get_database_config(env, base_dir):
    """PostgreSQL when configured, SQLite for local development.

    POSTGRES_HOST may be a Cloud SQL unix socket directory such as
    /cloudsql/project:region:instance, which psycopg accepts as a host.
    """
    database_name = env.get("POSTGRES_DB", "").strip()

    if database_name:
        return {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": database_name,
                "USER": env.get("POSTGRES_USER", ""),
                "PASSWORD": env.get("POSTGRES_PASSWORD", ""),
                "HOST": env.get("POSTGRES_HOST", ""),
                "PORT": env.get("POSTGRES_PORT", ""),
                "CONN_MAX_AGE": 60,
            }
        }

    if is_production(env):
        raise ImproperlyConfigured(
            "POSTGRES_DB must be set when DJANGO_ENV=production. SQLite would "
            "sit on an ephemeral disk and lose the ledger on redeploy."
        )

    return {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": base_dir / "db.sqlite3",
        }
    }


def get_security_settings(env):
    """HTTPS and cookie hardening, switched on together in production."""
    production = is_production(env)

    return {
        "SECURE_SSL_REDIRECT": production,
        "SECURE_PROXY_SSL_HEADER": (
            ("HTTP_X_FORWARDED_PROTO", "https") if production else None
        ),
        "SESSION_COOKIE_SECURE": production,
        "CSRF_COOKIE_SECURE": production,
        "SESSION_COOKIE_HTTPONLY": True,
        "SECURE_HSTS_SECONDS": ONE_YEAR_IN_SECONDS if production else 0,
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": production,
        "SECURE_HSTS_PRELOAD": production,
        "SECURE_CONTENT_TYPE_NOSNIFF": True,
        "X_FRAME_OPTIONS": "DENY",
    }


def check_email_configuration(env, backend, host):
    """Refuse to start in production with SMTP configured but no host.

    Password reset is the only way back into an account. If the mail settings
    are wrong the reset silently goes nowhere, and the failure only shows up
    when somebody is already locked out.
    """
    if not is_production(env):
        return

    if backend.endswith("smtp.EmailBackend") and not host:
        raise ImproperlyConfigured(
            "DJANGO_EMAIL_HOST must be set in production, or password reset "
            "emails will not be delivered. Set DJANGO_EMAIL_BACKEND "
            "explicitly if you intend not to send mail."
        )
