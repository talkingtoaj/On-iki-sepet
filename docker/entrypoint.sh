#!/bin/sh
set -e

# Migrations deliberately do NOT run here. On Cloud Run several containers can
# cold-start at once and would race the same migration. Run them as a
# pre-deploy step instead — see docs/deployment/runbook.md.
#
# Refuse to start if the settings are not production-ready, so a
# misconfiguration fails at boot rather than serving with debug on.
uv run python manage.py check --deploy --fail-level WARNING

exec "$@"
