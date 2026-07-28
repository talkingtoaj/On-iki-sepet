# KUT Finance Management System (On İki Sepet)

**Date:** 28.07.2026  
**Author:** Sezer Mintaz  
**Coach:** Andrew de Jonge

Django-based finance system for KUT Church. Tracks cash (ledger), bank accounts, and online donations in one place; keeps income, expenses, and transfers separate; reports TRY / USD / EUR without mixing currencies.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- SQLite (local; no extra setup)

## Setup

```bash
git clone <repo-url>
cd On-iki-sepet

uv sync
uv run python manage.py migrate
uv run python manage.py seed_demo_data
uv run python manage.py runserver
```

App: http://127.0.0.1:8000/  
Login: http://127.0.0.1:8000/accounts/login/

`seed_demo_data` creates groups, KUT accounts/categories, the admin user, demo users, and sample transactions.

To refresh demo transactions:

```bash
uv run python manage.py seed_demo_data --reset
```

### With pip

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

## Demo logins

| User | Password | Role |
|------|----------|------|
| `finans` | `DemoPass123!` | Data Entry — create transactions |
| `onaylayici` | `DemoPass123!` | Data Entry + Approver — create and approve |
| `lider` | `DemoPass123!` | Viewer — home and reports |
| `admin` | `qweqweqwe` | Superuser — Django admin |

For demo / local use only.

## Roles

| Group | Access |
|-------|--------|
| **Data Entry** | Create/edit transactions, lists, receipts, bank import |
| **Viewer** | Home summary and reports |
| **Approver** | Approval rights (with Data Entry) |

## Tests

```bash
uv run python manage.py test onikisepet
```

## Main URLs

| URL | Description |
|-----|-------------|
| `/` | Home |
| `/reports/` | Financial summary |
| `/transactions/` | Transaction list |
| `/imports/new/` | Bank statement import |
| `/accounts/` | Accounts |
| `/categories/` | Categories |
| `/admin/` | Django admin |

## Financial rules

- Transfers are neither income nor expense.
- TRY, USD, and EUR totals are never mixed.
- Transactions cannot be deleted; edits are written to an audit log.

## Environment variables

Copy `.env.example` to `.env` (do not commit).

| Variable | When |
|----------|------|
| `DJANGO_SECRET_KEY` | Required in production |
| `DJANGO_FILE_STORAGE_BACKEND` | `local` (default) or `gcs` |
| `GCS_MEDIA_BUCKET_NAME` | When using GCS |
| `GOOGLE_APPLICATION_CREDENTIALS` | When using GCS |

Locally, receipts are stored under `media/receipts/`.

Production packages: `uv sync --extra production`  
Operations: [`docs/deployment/runbook.md`](docs/deployment/runbook.md)

## Stack

Django 5.2 · Templates · SQLite (local) / PostgreSQL (production) · local disk or GCS
