# On İki Sepet

Church finance tracking: accounts, categorised income and expenses, transfers
between accounts, cash-expense receipts, bank-statement import, and
per-currency reporting with an audit trail.

Bilingual (Turkish and English) with a language selector. Django 5.2 + Django
Templates, SQLite locally and PostgreSQL in production.

## Requirements

* Python 3.13+
* [uv](https://docs.astral.sh/uv/) for dependency management

## Setup

```bash
uv sync                                     # create .venv, install locked deps
uv run python manage.py compilemessages -l tr   # build the Turkish catalogue
uv run python manage.py migrate
uv run python manage.py seed_roles          # Treasurer / Data Entry / Viewer
uv run python manage.py seed_kut_data       # chart of accounts and categories
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

`compilemessages` needs `gettext` installed (`apt install gettext`). The `.mo`
files are not committed, because a stale compiled catalogue fails silently.

`pyproject.toml` plus `uv.lock` are the single source of truth for dependencies.
There is no `requirements.txt`.

```bash
uv add <package>            # add a runtime dependency
uv add --dev <package>      # add a development-only dependency
uv lock --upgrade           # refresh the lock file
```

## Tests

```bash
uv run python manage.py test onikisepet                   # full app suite
uv run python manage.py test onikisepet.tests.test_x      # one focused file
```

The project follows the test-first rules in `onikisepet/docs/standards.md`.
Financial correctness is the highest priority; do not move on while tests fail.
### Continuous integration

`.github/workflows/ci.yml` runs on pull requests to `main`, on pushes to
`main`, and on demand via the Actions tab. There are no scheduled runs.

| Job | When | What |
| --- | --- | --- |
| Lint | every PR and push | `ruff check`, and `uv sync --locked` to catch a dependency change without a re-lock |
| Tests (SQLite) | every PR and push | Missing-migration check, then the full suite |
| Tests (PostgreSQL) | pushes to `main` only | The same suite against the engine production uses |

The PostgreSQL job asserts it really resolved to PostgreSQL before running,
because the settings fall back to SQLite when `POSTGRES_DB` is unset and the
job would otherwise pass while testing the wrong engine.


## Roles

Three roles are defined as Django groups. Create them once per environment:

```bash
uv run python manage.py seed_roles
```

| Role | Can do |
| --- | --- |
| `Treasurer` | Everything: accounts, categories, exchange rates, and correcting or voiding transactions |
| `Data Entry` | Post transactions and upload receipts; read everything else |
| `Viewer` | Read-only |

The books include donor records, so reading is a granted permission too: an
account with no role sees nothing. Assign roles in the Django admin.

## Configuration

Configuration comes from the environment. `DJANGO_ENV` defaults to
`development`; production has to be declared, and declaring it enforces a real
secret key, host list, PostgreSQL database and HTTPS. The rules live in
`config/env.py` and are covered by `onikisepet/tests/test_environment_config.py`.

### Development

Nothing is required. Optional overrides:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_ENV` | `development` | `development` or `production` |
| `DJANGO_DEBUG` | `1` in development | Set `0` to test with debug off |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1],testserver` | Comma-separated |
| `DJANGO_LANGUAGE_CODE` | `tr` | Default interface language |
| `DJANGO_TIME_ZONE` | `Europe/Istanbul` | Reporting dates follow this, not the server clock |

### Production (`DJANGO_ENV=production`)

| Variable | Required | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | yes | At least 50 characters and 5 distinct ones |
| `DJANGO_ALLOWED_HOSTS` | yes | Comma-separated hostnames |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | no | Comma-separated origins, e.g. `https://app.example.org` |
| `POSTGRES_DB` | yes | SQLite is refused: on Cloud Run it sits on an ephemeral disk |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | yes | Database credentials |
| `POSTGRES_HOST` | yes | Hostname, or a Cloud SQL socket such as `/cloudsql/project:region:instance` |
| `POSTGRES_PORT` | no | Omit when using a socket |
| `GS_BUCKET_NAME` | no | Enables Google Cloud Storage for receipts |
| `GS_LOCATION` | no | Prefix within the bucket, default `receipts` |
| `DJANGO_EMAIL_HOST` | yes | Required for password reset; boot fails without it |
| `DJANGO_EMAIL_PORT` / `_USER` / `_PASSWORD` / `_USE_TLS` | no | SMTP details |
| `DJANGO_DEFAULT_FROM_EMAIL` | no | Sender address for reset emails |

Generate a secret key with:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Production turns on `SECURE_SSL_REDIRECT`, HSTS for one year, secure and
HTTP-only cookies, `X-Frame-Options: DENY`, and trusts
`X-Forwarded-Proto` because Cloud Run terminates TLS upstream. Static files are
served by Whitenoise, so run `collectstatic` as part of the build.

Verify a configuration before deploying:

```bash
DJANGO_ENV=production ... uv run python manage.py check --deploy
```

Receipts must not be publicly readable. With `GS_BUCKET_NAME` set, URLs are
signed and expire after 15 minutes; keep the bucket private.

## Deployment

`Dockerfile` builds with uv against the lock file, collects static files and
compiles translations at build time, and runs unprivileged. Migrations
deliberately do **not** run from the entrypoint — Cloud Run cold-starts several
containers at once and they would race the same migration.

`GET /health/` reports database reachability for the platform health check.
`scripts/backup_database.sh` takes a dump before a risky migration.

Full procedure, including first-time setup and rollback: see
[`docs/deployment/runbook.md`](docs/deployment/runbook.md).

Note on dependencies: gunicorn, psycopg and django-storages are plain runtime
dependencies rather than an optional `production` extra. The extra saves a few
megabytes in development but risks a deploy or a CI job running without them,
which is the more expensive failure.

## Project layout

```
config/                 Django project settings and root URLconf
onikisepet/
    models.py           Category, Account, Transaction, Receipt
    forms.py            Form-level validation
    views.py            Server-rendered views
    usecases/           Testable financial logic, kept out of views/templates
        financial_calculations.py   Per-currency totals, balances, conversion
        audit.py                    Transaction create/edit/void + audit trail
        roles.py                    Role definitions and seeding
    validators.py       Receipt upload validation
config/env.py           Environment-driven configuration rules
    templates/
    tests/              Split by responsibility: model / form / views / rules
    docs/standards.md   Development standards for this project
PLAN.md                 Current hardening work plan
```
