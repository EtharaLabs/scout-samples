#!/bin/bash
# Reference implementation. Never shipped to the solver.
#
# fix.patch is the reference, bounded to the graded objective: fifty source files under dvc/, 92 KB.
# It is measured to resolve all one hundred and seven required nodes with zero regressions against
# the baseline manifest, so the oracle scores full reward on it.
#
# The bound is three files narrower than the release's own package change. Those three live under
# dvc/testing/, which seventeen graded test files import fixtures from, so handing them to a solver
# would let it edit fixtures instead of implementing the release. Bounding alone was measured and
# fails: two must-keep nodes inherit from dvc/testing/remote_tests.py and regress, giving 2875 of
# 2880. The verifier therefore restores dvc/testing from the target revision in test.sh step 2,
# which was measured to recover both nodes and return the oracle to full reward.
#
# span_diff.patch beside it is the whole release span, seventy-four files and 168 KB including
# tests, CI configuration and packaging. That is provenance, never the reference.
#
# Neither patch carries test bytes. The verifier owns the test trees, so the reference cannot pass
# the grade by editing what grades it.
#
# The diff is in git's own format, so git applies it. The environment ships git and no `patch`.
set -uo pipefail

WORK=/app
PATCH="$(cd "$(dirname "$0")" && pwd)/fix.patch"

cd "$WORK" || exit 1

# Exact-path apply, as the run contract's patch_apply.exact_path fixes it.
if git apply -p1 --whitespace=nowarn "$PATCH"; then
  echo "solve: applied at exact path"
  exit 0
fi

# Recorded fallback, attempted before the grade may be recorded as unapplied.
echo "solve: exact-path apply failed, attempting recorded fallback" >&2
if git apply -p1 -C1 --recount --whitespace=nowarn "$PATCH"; then
  echo "solve: applied via recorded fallback"
  exit 0
fi

echo "solve: unapplied" >&2
exit 1
