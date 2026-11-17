#!/usr/bin/env bash
# Reference solution: apply the release's source-side change set.
# The patch touches only celery/ ; the t/ test tree is supplied by the verifier.
set -euo pipefail
cd "${1:-/app}"
patch -p1 --batch --forward --remove-empty-files < "$(dirname "$0")/fix.patch"
python -c "import celery; print('celery import ok', celery.__version__)"
