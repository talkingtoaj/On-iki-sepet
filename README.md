# On İki Sepet

Church finance tracking: accounts, categorised income and expenses, transfers
between accounts, cash-expense receipts, and per-currency reporting.

Django 5.2 + Django Templates, SQLite locally and PostgreSQL in production.

## Requirements

* Python 3.13+
* [uv](https://docs.astral.sh/uv/) for dependency management

## Setup

```bash
uv sync                     # create .venv and install locked dependencies
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

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
