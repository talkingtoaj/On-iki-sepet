#!/bin/sh
set -e

# Migrations run as a Cloud Build pre-deploy step (cloudbuild.yaml),
# not here — avoids concurrent-cold-start migration races on Cloud Run.
exec "$@"
