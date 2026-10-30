#!/bin/bash
# Verifier entry point for the release-evolution dvc task.
#
# [verifier].environment_mode is "separate", so this runs in a fresh container the agent never
# touched. Only the artifacts task.toml declares were transferred in; everything else under /app
# is pristine base-revision source baked into this image.
#
# This script prepares state and then hands scoring to Harbor Reward Kit. It writes no reward
# bytes of its own: Reward Kit is the whole path from criterion outcome to /logs/verifier/
# reward.json, and it attributes every zero to a machine-readable reason.
set -uo pipefail

WORK=/app
cd "$WORK" || exit 1

# ---------------------------------------------------------------------------------------------
# 0. Scorer state lives in a private directory, never at a predictable path under /tmp.
#
#    A fixed /tmp/junit.xml is a world-writable rendezvous point: agent code imported during
#    collection knows exactly where to write. mktemp gives an unpredictable directory at 0700
#    owned by this process. That raises the cost of the attack; it does not close it, because the
#    pytest child inherits this environment. Closing it needs launcher-versus-runner uid
#    separation and an append-only pipe, which this image does not yet provide.
# ---------------------------------------------------------------------------------------------
STATE="$(mktemp -d)" || exit 1
chmod 700 "$STATE"
export VERIFIER_STATE="$STATE"

# ---------------------------------------------------------------------------------------------
# 1. Red line RL-NO-TEST-EDIT, captured before the authoritative trees are restored.
#
#    /opt/shipped/tests is the test tree exactly as the agent image shipped it. The uploaded
#    artifact is the same tree as the solver left it.
#
#    The rule distinguishes two acts. Modifying or deleting a test the verifier runs is the red
#    line. ADDING a test file is permitted: writing tests for a feature is the characteristic
#    behaviour of competent release engineering, and the real upstream pull requests did exactly
#    that. An added file is discarded with the rest of the solver's copy at step 2, so it can
#    never buy a grade either. Only the pre-existing paths are compared.
# ---------------------------------------------------------------------------------------------
digest_tree() {
  ( cd "$1" 2>/dev/null && find . -type f -name '*.py' -print0 | sort -z | xargs -0 sha256sum )
}
digest_tree "$WORK/tests"     > "$STATE/graded-tests.sha256" 2>/dev/null
digest_tree /opt/shipped/tests > "$STATE/shipped-tests.sha256" 2>/dev/null

sort "$STATE/shipped-tests.sha256" > "$STATE/shipped-sorted.sha256"
awk 'NR==FNR { keep[$2] = 1; next } ($2 in keep)' \
  "$STATE/shipped-tests.sha256" "$STATE/graded-tests.sha256" \
  | sort > "$STATE/graded-preexisting.sha256"

if diff -q "$STATE/shipped-sorted.sha256" "$STATE/graded-preexisting.sha256" >/dev/null 2>&1; then
  echo 0 > "$STATE/tests_modified"
else
  echo 1 > "$STATE/tests_modified"
fi
echo "verifier: tests_modified=$(cat "$STATE/tests_modified")"
echo "verifier: added_test_files=$(( $(wc -l < "$STATE/graded-tests.sha256") - $(wc -l < "$STATE/graded-preexisting.sha256") ))"

# ---------------------------------------------------------------------------------------------
# 2. Restore the authoritative trees. The solver never received these bytes, and whatever it did
#    to its own copy is discarded here, so editing a test can be recorded but can never buy a
#    passing grade.
#
#    dvc/testing is restored for the same reason, from the TARGET revision. It is the test-support
#    package the graded tree imports, seventeen graded files import dvc.testing, and it ships
#    inside /app/dvc which the artifacts list admits. Restoring it from base is not available: the
#    reference needs three files there, measured as exactly two must-keep regressions when they
#    are withheld. Restoring from target reaches 111/111 required and 2880/2880 held, so the
#    vector closes at zero oracle cost and those three files are given rather than derived.
# ---------------------------------------------------------------------------------------------
#    The restore happens in a verifier-owned copy, never in /app. The solver owns /app as uid
#    10001 and this script runs as 10002, so `rm -rf "$WORK/tests"` is EPERM there: the restore
#    would fail file by file, the solver's own test tree would survive, and the grade would be
#    measured against bytes the solver controls. Copying first is what makes the restore real.
# A FIXED path, not one under the private mktemp state. Several of this suite's parametrized
# tests render the absolute working directory into their own node id, so a per-run temporary
# directory would rename those nodes on every run and the predeclared sets could never match.
# The directory is verifier-owned and recreated here, so a stale tree cannot survive between runs.
GRADED=/graded
rm -rf "$GRADED"
mkdir -p "$GRADED"
cp -R "$WORK/." "$GRADED/" 2>/dev/null

# /app files can arrive mode 0555, which makes the restore below EPERM even inside the copy.
chmod -R u+rwX "$GRADED" 2>/dev/null

rm -rf "$GRADED/tests"
cp -RT /opt/authoritative/tests "$GRADED/tests"

rm -rf "$GRADED/dvc/testing"
cp -RT /opt/authoritative/dvc-testing "$GRADED/dvc/testing"

# Fail closed. A restore that silently half-applied would grade the wrong tree, and that bug
# class is otherwise invisible in the reward: it looks like a solver that simply scored badly.
if [ -d "$GRADED/tests/tests" ]; then
  echo "verifier: restore nested the test tree, refusing to grade" >&2
  exit 1
fi
if [ ! -f "$GRADED/tests/func/test_checkout.py" ]; then
  echo "verifier: authoritative test tree is not in place, refusing to grade" >&2
  exit 1
fi
if [ ! -f "$GRADED/dvc/testing/remote_tests.py" ]; then
  echo "verifier: dvc/testing restore is not in place, refusing to grade" >&2
  exit 1
fi
echo "verifier: graded_tree=$GRADED"

# ---------------------------------------------------------------------------------------------
# 3. Run the repository's own entry points, identically for the real upstream artifact and a
#    model submission. tests/integration is absent from the authoritative tree because it requires
#    network services this task denies, and test_import_db.py is excluded because it needs a
#    database service.
#
#    tests/remotes DOES ship, and is then ignored here. It carries no graded node and its own
#    tests need network, so running it is pointless. But the root tests/conftest.py line 13 is
#    `from .remotes import *`, so omitting the package makes that conftest unimportable and
#    pytest exits 4 having collected nothing at all. It ships to satisfy the import and is
#    ignored to keep it from running.
#
#    The report goes to the private state directory, so a transferred artifact cannot know the
#    path at build time. `-o addopts=` discards any addopts a transferred pytest.ini or setup.cfg
#    would otherwise inject, and --confcutdir stops conftest discovery walking above the tree
#    being run. PYTHONDONTWRITEBYTECODE keeps a stale .pyc from shadowing a restored test.
#
#    Not yet closed: plugin autoload still runs, so a .pth, sitecustomize, or a pytest11 entry
#    point in a transferred artifact executes before collection. Disabling autoload needs the
#    suite's required plugin list proven against the image first, because a wrong list breaks
#    collection for the oracle too.
# ---------------------------------------------------------------------------------------------
cd "$GRADED" || exit 1
python -m pytest tests/unit tests/func \
  -q -p no:cacheprovider --no-header \
  -o addopts= \
  --confcutdir="$GRADED/tests" \
  --timeout=300 \
  --ignore="$GRADED/tests/func/test_import_db.py" \
  --ignore="$GRADED/tests/remotes" \
  --continue-on-collection-errors \
  --junit-xml="$STATE/junit.xml"
echo "verifier: pytest exit=$?"

# ---------------------------------------------------------------------------------------------
# 4. Score. Reward Kit imports tests/test_output.py, runs every registered criterion, and writes
#    the reward carrier Harbor reads.
# ---------------------------------------------------------------------------------------------
# The judged channel reads one file, named statically in judge.toml, so its evidence is
# produced here at that exact path. diff exits 1 when the trees differ, which is the normal
# case, so its status is not an error.
mkdir -p /logs/verifier
diff -ruN /opt/pristine-dvc "$GRADED/dvc" > /logs/verifier/final.diff 2>/dev/null || true
echo "verifier: judged evidence $(wc -c < /logs/verifier/final.diff | tr -d ' ') bytes"

exec rewardkit /tests --workspace "$GRADED" --output /logs/verifier/reward.json
