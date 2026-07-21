#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.."
OUT=".test-mvp-run.txt"
.venv/bin/python manage.py test onikisepet 2>&1 | tee "$OUT"
exit_code=${PIPESTATUS[0]}
echo "EXIT:${exit_code}" >> "$OUT"
exit "${exit_code}"
