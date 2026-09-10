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

## Database lineage

**This code needs an empty database, and it will not migrate one that belongs
to the other lineage.** That is enforced in the deploy pipeline, not just
written down here, because the failure it prevents is destructive.

The collaborator's branch and this one both migrated from a common ancestor at
`0006`, then diverged. Migration numbers `0007` through `0011` exist in both
lineages describing different schema changes:

| Number | This lineage | Deployed lineage |
| --- | --- | --- |
| `0007` | `exchangerate` | `auditlog` |
| `0008` | transaction options, receipt file | `transaction_approval` |
| `0009` | `is_void`, `void_reason` | `profile` |
| `0010` | category and receipt alterations | `receipt_file_type` |
| `0011` | `bankstatementimport`, `bankstatementrow` | `bank_statement_import` |

Theirs continues to `0020`; ours ends at `0011`. The numbers collide but the
migration *names* do not, and Django records applied migrations by name. So
running `migrate` from this lineage against the deployed database would not
skip anything: it would find our `0006_receipt` applied, then try to apply
`0007_exchangerate` onward on top of their schema.

The first few would succeed, because `exchangerate` and the void columns do not
exist in their lineage. `0011` would then fail, because both lineages declare
models named `BankStatementImport` and `BankStatementRow` in the `onikisepet`
app with no `db_table` override, so both want the same two tables and theirs
are already there.

That is the dangerous part. On PostgreSQL each migration commits in its own
transaction, so the failure arrives *after* `0007`-`0010` have already been
committed to the live database. A deploy would leave the church's production
schema half-migrated onto a lineage it does not belong to, with a failed build
and no automatic rollback of what already applied.

### The decision

**The existing `oniki_sepet` database is wiped and rebuilt from this lineage,
and this lineage deploys over the existing `kut-finans` Cloud Run service.**
Names stay as they are, so no connection strings change.

Be clear about what that costs: **the deployed church finance data is
destroyed.** It is not migrated, and there is no reconciling migration. Anything
in there that matters must be exported and re-entered against this schema by
hand, because the two schemas disagree about what a transaction is. The
collaborator owns that instance, so they need to have agreed before the drop.

The Cloud Build trigger `on-iki-sepet` is deliberately **left enabled**. It
watches `^main$` on `talkingtoaj/On-iki-sepet` and runs `cloudbuild.yaml`, so a
merge to `main` deploys.

### Why ordering is safety-critical, and what protects it

With the trigger enabled, the wipe must happen **before** anything reaches
`main`. Merge first and the migrate step meets the collaborator's schema and
half-migrates it, as above.

That ordering is not left to whoever is holding the mouse. `cloudbuild.yaml`
runs a `check-lineage` step before `migrate`:

```bash
uv run python manage.py check_database_lineage
```

It compares the migrations recorded in the database against the migration files
in this branch and exits non-zero if the database has any this branch does not
contain. So merging before the wipe produces a **failed build that has written
nothing**, rather than a half-migrated ledger. The logic is in
`onikisepet/usecases/database_lineage.py` and covered by
`onikisepet/tests/test_database_lineage.py`.

Run it by hand against Cloud SQL any time you want to know which lineage a
database is on.

### Prerequisites before the first deploy

`cloudbuild.yaml` needs two secrets that do not exist yet, and three
substitutions the trigger must supply. It intentionally gives the mail
substitutions no defaults: an unset one fails the build while it is still
parsing, which is far better than a container that boots, fails
`check --deploy`, and never serves.

The Postgres password is already inside the old `oniki-sepet-database-url`
secret. Copy it across without printing it:

```bash
gcloud secrets versions access latest --secret=oniki-sepet-database-url \
  | sed -E 's|^.*://[^:]+:([^@]+)@.*$|\1|' \
  | tr -d '\n' \
  | gcloud secrets create oniki-sepet-postgres-password --data-file=-

# The mail account password for password-reset delivery
printf '%s' 'THE_SMTP_PASSWORD' \
  | gcloud secrets create oniki-sepet-email-password --data-file=-
```

Then set `_EMAIL_HOST`, `_EMAIL_USER` and `_FROM_EMAIL` on the trigger:

```bash
gcloud builds triggers update github on-iki-sepet \
  --update-substitutions=_EMAIL_HOST=smtp.example.org,_EMAIL_USER=finance@example.org,_FROM_EMAIL=finance@example.org
```

### Cutover, in order

Do not reorder these. Steps 1 and 2 are the ones that cannot be undone.

```bash
# 1. Back up what is about to be destroyed. Verify the file before continuing.
gcloud sql export sql lb-db2 gs://YOUR_BACKUP_BUCKET/oniki_sepet-precutover.sql.gz \
  --database=oniki_sepet --project=lifebalance-nuxt

# 2. Drop and recreate the database. This destroys the deployed data.
gcloud sql databases delete oniki_sepet --instance=lb-db2 --project=lifebalance-nuxt
gcloud sql databases create oniki_sepet --instance=lb-db2 --project=lifebalance-nuxt

# 3. Confirm the database is now on no lineage at all. Expect a clean pass.
#    Run from a machine with the Cloud SQL proxy up.
uv run python manage.py check_database_lineage

# 4. Merge the PR. The trigger builds, re-checks the lineage, migrates the
#    empty database and deploys over kut-finans.

# 5. Seed the empty database and create the first account.
uv run python manage.py seed_roles
uv run python manage.py seed_kut_data
uv run python manage.py createsuperuser
```

Then assign roles in the Django admin, as under **First-time setup** below.

If step 4 fails on `check-lineage`, the wipe in step 2 did not happen or did not
take. Nothing has been written; fix the database and re-run the build.

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
