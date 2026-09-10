# Deployment runbook

The app runs as a container on Cloud Run, against Cloud SQL for PostgreSQL,
with receipts in Google Cloud Storage.

## Configuration

Everything comes from the environment. `DJANGO_ENV=production` must be set
explicitly; setting it enforces debug off, a real secret key, a real host list,
PostgreSQL, HTTPS and a working mail host. The rules live in `config/env.py`
and are covered by `onikisepet/tests/test_environment_config.py`.

See the Configuration table in `README.md` for every variable. The required
ones in production are:

| Variable | Notes |
| --- | --- |
| `DJANGO_ENV` | `production` |
| `DJANGO_SECRET_KEY` | 50+ characters, 5+ distinct. Store in Secret Manager |
| `DJANGO_ALLOWED_HOSTS` | The Cloud Run hostname and any custom domain |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://` origins for the same hosts |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Cloud SQL credentials |
| `POSTGRES_HOST` | The socket path, `/cloudsql/PROJECT:REGION:INSTANCE` |
| `DJANGO_EMAIL_HOST` and credentials | Password reset will not work without it |
| `GS_BUCKET_NAME` | Receipts bucket. Keep it private |

Verify a configuration before deploying:

```bash
DJANGO_ENV=production DJANGO_SECRET_KEY=... DJANGO_ALLOWED_HOSTS=... \
  POSTGRES_DB=... POSTGRES_HOST=... DJANGO_EMAIL_HOST=... \
  uv run python manage.py check --deploy
```

## Build

```bash
docker build -t onikisepet .
```

The build collects static files and compiles the Turkish catalogue, so neither
happens on a cold start. The placeholder secret used during the build is not
retained in the image's runtime configuration.

## Migrations

**Run migrations as a pre-deploy step, never from the container entrypoint.**
Cloud Run can cold-start several containers at once and they would race the
same migration. The entrypoint only runs `check --deploy`, so a
misconfiguration fails at boot instead of serving with debug on.

```bash
# Against Cloud SQL, from a machine with the proxy or from a Cloud Build step
uv run python manage.py migrate
```

## First-time setup

In order:

```bash
uv run python manage.py migrate
uv run python manage.py seed_roles        # Treasurer / Data Entry / Viewer
uv run python manage.py seed_kut_data     # chart of accounts and categories
uv run python manage.py createsuperuser
```

Then assign each person a role in the Django admin. A signed-in account with
no role sees a "waiting for access" page rather than the books, so nothing is
exposed before a role is granted deliberately.

## Health

`GET /health/` returns 200 with `{"status": "ok"}` when the database answers,
and 503 when it does not. It requires no authentication, because the platform's
checker cannot sign in, and it reveals nothing beyond reachability. Point the
Cloud Run health check at it.

## Backups

```bash
POSTGRES_DB=... POSTGRES_HOST=... POSTGRES_USER=... POSTGRES_PASSWORD=... \
  ./scripts/backup_database.sh
```

Writes a timestamped custom-format dump to `./backups`. Restore with
`pg_restore --dbname=... --clean <file>`.

Cloud SQL automated backups should be on as well; this script is for taking a
dump before a risky migration.

## Receipts

Receipts hold financial information about named people. The bucket must not be
public: with `GS_BUCKET_NAME` set, URLs are signed and expire after 15 minutes,
and the storage backend sets no public ACL. Check the bucket's own permissions
too; the application cannot make a public bucket private.

## Rolling back

Cloud Run keeps previous revisions, so redirect traffic to the last good one.
Note that a rollback does **not** revert a migration. If the bad deploy
migrated the database, restore from a dump taken beforehand, which is why the
backup step above precedes risky migrations.
