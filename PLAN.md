# Feature Plan — localization plus selected features from upstream

Work agreed after reviewing `origin/main` (the collaborator's diverged branch).
We keep our own lineage and reimplement the features worth having, rather than
merging 24k lines with 30 conflicts and colliding migration numbers.

## Decisions taken

* **Localization is proper i18n, not hardcoded Turkish.** Upstream hardcoded
  Turkish strings with no `gettext`. We wrap everything in `gettext` and ship a
  Turkish catalogue plus a language selector, so both languages are available.
* **Roles stay admin-assigned.** No role-management UI. "User management"
  therefore reduces to a pending-access page for signed-in users who have no
  role yet, instead of the blunt 403 they get today.
* **Money input accepts both formats.** `1.234,56` (Turkish) and `1234.56`
  (plain) both parse, rather than forcing one convention.
* **Migrations continue our lineage** from 0011. Reconciling the deployed
  database, which sits at upstream's 0020, is a separate deployment decision
  still to be made.

## Not doing (explicitly declined)

* Approval / reject / resubmit workflow — not a client requirement.
* Account change requests.
* Purpose-specific entry forms (separate cash-income / bank-expense routes).
* htmx dashboard partials — extra frontend layer the standards doc avoids.

---

## Phase 1 — Internationalisation

Done first so every later feature is written localised, avoiding a second pass.

* [x] `LocaleMiddleware`, `LOCALE_PATHS`, `LANGUAGES = [tr, en]`, env-driven default
* [x] `TIME_ZONE` default to `Europe/Istanbul` (reporting dates depend on it)
* [x] Wrap every user-facing Python string in `gettext_lazy`
* [x] Wrap every template string in `{% translate %}` / `{% blocktranslate %}`
* [x] Turkish catalogue, reusing upstream's wording where it fits
* [x] Language selector in the base template, via `set_language`
* [x] Tests: both languages render, selection persists, catalogue has no gaps
* [x] `compilemessages` wired into the container build

## Phase 2 — Money input accepting both formats

* [x] `parse_localized_decimal` handling `1.234,56`, `1234.56`, `1 234,56`
* [x] Form field + widget used by every amount input
* [x] Display formatting follows the active locale
* [x] Tests: ambiguous cases, thousands separators, rejection of real garbage

## Phase 3 — Report periods

* [x] `resolve_report_period`: this month, last month, this year, all time
* [x] Dashboard filter control, with the active range shown
* [x] Tests: boundaries, and that a period never leaks a transaction

## Phase 4 — Password reset

* [x] The five reset templates, localised (the views are already mounted)
* [x] Email settings via environment
* [x] Tests: full reset flow end to end

## Phase 5 — Pending access

* [x] A signed-in user with no role sees an explanatory page, not a 403
* [x] Tests: role-less user is guided, roled users unaffected

## Phase 6 — Guide pages

* [x] Finance guide and record-type guide, adapted and localised
* [x] Linked from the navigation

## Phase 7 — KUT seed data

* [x] Chart of accounts and categories from upstream, as a management command
* [x] Idempotent, and safe to run against an existing database
* [x] Tests: seeding twice changes nothing the second time

## Phase 8 — Bank statement import

The largest piece. Upload, preview, then confirm; nothing is written until the
treasurer confirms.

* [x] `BankStatementImport` and `BankStatementRow` models
* [x] CSV, XLSX and PDF readers
* [x] Turkish bank column aliases and header mapping
* [x] Row parsing: dates, amounts, currencies, account resolution
* [x] Per-row classification, skipping, and parse-error capture
* [x] Upload → preview → confirm views, creating transactions on confirm
* [x] Sample CSV download
* [x] Tests: each format, malformed rows, duplicate protection, permissions

## Phase 9 — Deployment

* [x] `Dockerfile` and entrypoint, with `collectstatic` and `compilemessages`
* [x] `/health` endpoint for Cloud Run
* [x] Database backup script
* [x] Deployment runbook, updated for our settings module
* [x] Move gunicorn/psycopg/storages into an optional `production` extra
* [x] Tests: deployment settings and the health endpoint

---

## Deliberate deviations from upstream

* **Amount parsing is stricter.** Upstream read dot-only input as a decimal, so
  a Turkish `1.234` became 1.234 — a thousandfold understatement. Ours resolves
  the ambiguity by decimal-place count and refuses what it cannot read.
* **Import refuses a mis-delimited line.** An unquoted `2.750,50` in a
  comma-delimited file split across columns and read as `2750` upstream. Ours
  detects the column-count mismatch and reports it.
* **Localisation is real i18n**, not hardcoded Turkish, so English still works.
* **Roles stay admin-assigned.** No role-management UI; a role-less account
  gets a "waiting for access" page instead of a bare 403.
* **Production dependencies are not an optional extra.** Upstream put gunicorn,
  psycopg and django-storages behind `[production]`. That saves a few megabytes
  in development and risks a deploy or CI job running without them.
* **No plural message forms.** Turkish takes the singular after a numeral, so
  count-agnostic phrasing is used instead of `ngettext`.

## Still open

* **The deployed database is on upstream's migration lineage (0020).** Ours
  ends at 0011 and knows nothing of their `Profile`, `AccountChangeRequest` or
  approval columns. Reconciling that is a deployment decision, not a code one,
  and it is still unmade.
* **`cloudbuild.yaml` is not carried over.** Their pipeline migrates and
  deploys on push to main; pointing it at this lineage needs the database
  question answered first.
