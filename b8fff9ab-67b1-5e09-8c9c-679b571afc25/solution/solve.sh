#!/usr/bin/env bash
# Reference solution: apply the release's source-side change set.
# The patch touches only sympy/ source modules; every sympy/**/tests/ subtree is supplied by the
# verifier from the target revision, so no test bytes are in this patch.
set -euo pipefail
cd "${1:-/app}"
patch -p1 --batch --forward --remove-empty-files < "$(dirname "$0")/fix.patch"
python -c "import sympy; print('sympy import ok', sympy.__version__)"
