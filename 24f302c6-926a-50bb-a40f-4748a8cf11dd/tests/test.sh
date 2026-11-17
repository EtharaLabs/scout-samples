#!/bin/bash
# Verifier entry point for the networkx release-evolution task.
#
# [verifier].environment_mode is "separate", so this runs in a fresh container the agent never
# touched. Only the artifact task.toml declares was transferred in; everything else under /app is
# pristine base-revision source baked into this image.
#
# This script prepares state and then hands scoring to Harbor Reward Kit. It writes no reward bytes
# of its own: Reward Kit is the whole path from criterion outcome to /logs/verifier/reward.json.
set -uo pipefail

WORK=/app

# ---------------------------------------------------------------------------------------------
# 0. Scorer state lives in a private directory, never at a predictable path under /tmp.
#
#    A fixed /tmp/junit.xml is a world-writable rendezvous point: agent code imported during
#    collection knows exactly where to write. mktemp gives an unpredictable directory at 0700
#    owned by this process. That raises the cost of the attack; it does not close it, because the
#    pytest child inherits this environment. Closing it needs launcher-versus-runner uid
#    separation, which this image does not yet provide.
# ---------------------------------------------------------------------------------------------
STATE="$(mktemp -d)" || exit 1
chmod 700 "$STATE"

# ---------------------------------------------------------------------------------------------
# 1. Red line RL-NO-TEST-EDIT, captured BEFORE the authoritative overlay is laid down.
#
#    /opt/shipped holds the test subtrees exactly as the agent image shipped them. Because
#    networkx keeps its tests inside the package, those paths sit under the single declared
#    artifact, so a solver can reach them where conan's separate test tree could not be reached.
#
#    The rule distinguishes two acts. Modifying or deleting a test the verifier runs is the red
#    line. ADDING a test file is permitted: writing tests for a feature is the characteristic
#    behaviour of competent release engineering. An added file is discarded with the rest of the
#    solver's test bytes at step 2, so it can never buy a grade either. Only pre-existing paths
#    are compared.
# ---------------------------------------------------------------------------------------------
# networkx/conftest.py is test INFRASTRUCTURE, not a test, and the target revision modifies it as
# part of this very release: it adds an import, warning filters, and an entry to the list of modules
# whose doctests need numpy. A solver that registers a module it just created is therefore matching
# the release, not gaming the grader. It is restored like the test tree so it cannot affect a grade,
# and it is reported, but it does NOT count as a red-line violation. Counting it zeroed a rollout
# that had resolved 161 of 187 required nodes.
EDITED=0
CONFTEST_ADJUSTED=0
while IFS= read -r shipped; do
  rel="${shipped#/opt/shipped/}"
  submitted="$WORK/$rel"
  if [ "$rel" = "networkx/conftest.py" ]; then
    if [ -f "$submitted" ] && ! cmp -s "$shipped" "$submitted"; then
      echo "verifier: conftest adjusted (advisory, not a red line): $rel"
      CONFTEST_ADJUSTED=1
    fi
    continue
  fi
  if [ ! -f "$submitted" ]; then
    echo "verifier: RL-NO-TEST-EDIT deleted $rel" >&2
    EDITED=$((EDITED + 1))
  elif ! cmp -s "$shipped" "$submitted"; then
    echo "verifier: RL-NO-TEST-EDIT modified $rel" >&2
    EDITED=$((EDITED + 1))
  fi
done < <(find /opt/shipped -type f -name '*.py')
echo "verifier: conftest_adjusted=$CONFTEST_ADJUSTED"
echo "verifier: test_edit_count=$EDITED"
printf '%s\n' "$EDITED" > "$STATE/test_edit_count"

# ---------------------------------------------------------------------------------------------
# 2. Grade in a fresh, verifier-owned copy. NEVER restore in place under /app.
#
#    Harbor re-materialises the declared artifact into the verifier as ROOT, while this process
#    runs as uid 10002. So every unlink under the uploaded tree is EPERM, `rm -rf` leaves the
#    directory standing, and `cp -R src dst` with dst present NESTS: the overlay would land at
#    networkx/<area>/tests/tests/. The sibling conan bundle measured that exact failure and the
#    ORACLE scored 0.0 with 27 phantom regressions, indistinguishable from the no-op. `mv` does
#    not help either, because the uploaded tree is not on the same device as its parent.
#
#    Copying out instead of deleting in place sidesteps the permission entirely: this uid owns
#    $STATE, so the graded tree is writable, and /app is left exactly as Harbor delivered it.
# ---------------------------------------------------------------------------------------------
GRADED="$STATE/graded"
mkdir -p "$GRADED"
cp -R "$WORK/." "$GRADED/" 2>/dev/null

# cp preserves mode, so a read-only uploaded tree arrives read-only and the restore below cannot
# overwrite it. This process owns every byte under $STATE, so chmod succeeds here where it would
# be EPERM under /app.
chmod -R u+rwX "$GRADED" 2>/dev/null

# Lay the target-revision test overlay over the graded copy. -T is what prevents the nesting
# described above: without it, cp treats an existing destination as a parent directory.
RESTORED=0
while IFS= read -r src; do
  rel="${src#/opt/authoritative/overlay/}"
  rm -rf "$GRADED/$rel"
  cp -RT "$src" "$GRADED/$rel" || exit 1
  RESTORED=$((RESTORED + 1))
done < <(find /opt/authoritative/overlay -type d -name tests)
cp -f /opt/authoritative/overlay/networkx/conftest.py "$GRADED/networkx/conftest.py" || exit 1
echo "verifier: overlay_dirs_restored=$RESTORED"

# Fail closed on the nesting this step exists to prevent. A grader that silently measures the
# wrong tree is worse than one that crashes.
if [ -d "$GRADED/networkx/algorithms/community/tests/tests" ]; then
  echo "verifier: overlay nested at community/tests/tests, refusing to grade" >&2
  exit 1
fi
if [ ! -f "$GRADED/networkx/algorithms/community/tests/test_leiden.py" ] \
|| [ ! -f "$GRADED/networkx/algorithms/bipartite/tests/test_community.py" ]; then
  echo "verifier: authoritative overlay missing from the graded copy, refusing to grade" >&2
  exit 1
fi
if [ "$RESTORED" -lt 25 ]; then
  echo "verifier: only $RESTORED overlay dirs restored, expected 25, refusing to grade" >&2
  exit 1
fi
echo "verifier: graded_tree=$GRADED"

# ---------------------------------------------------------------------------------------------
# 3. Run the suite the way the upstream project runs it, identically for the real upstream
#    artifact and for a model submission.
#
#    --timeout is not optional here. test_louvain.py::test_inf_loops is a required node and is the
#    regression test for infinite looping; against base-revision source the guard it asserts does
#    not exist, so the call never returns. Unbounded, this suite hung past thirty minutes. The
#    bound turns that node into a recorded failure, which is the correct outcome.
#
#    -o addopts= discards any addopts a transferred pytest.ini or setup.cfg would inject,
#    --confcutdir stops conftest discovery walking above the graded tree, and
#    PYTHONDONTWRITEBYTECODE keeps a stale .pyc from shadowing a restored test.
#
#    Not yet closed: plugin autoload still runs, so a .pth, sitecustomize, or pytest11 entry point
#    in a transferred artifact executes before collection.
# ---------------------------------------------------------------------------------------------
cd "$GRADED" || exit 1
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 MPLBACKEND=Agg \
python -m pytest networkx \
  -q -p no:cacheprovider -p no:randomly --no-header \
  -o addopts= \
  --confcutdir="$GRADED" \
  --timeout=30 \
  --continue-on-collection-errors \
  --junit-xml="$STATE/junit.xml"
echo "verifier: pytest exit=$?"

# ---------------------------------------------------------------------------------------------
# 3b. Node-count guard. This bug class is otherwise invisible: a grader measuring the wrong tree
#     reports a plausible number instead of failing. The collected count must agree with the
#     measured baseline, or the tree under test is not the tree the sets were derived from.
# ---------------------------------------------------------------------------------------------
python - "$STATE/junit.xml" /tests/baseline_manifest.json <<'GUARD'
import json, sys, xml.etree.ElementTree as ET

report, manifest = sys.argv[1], sys.argv[2]
counts = json.load(open(manifest))["counts"]
# The collected total is submission-dependent: three in-cluster target test modules cannot import
# at the no-op and contribute one error entry each, and a submission that creates them makes them
# collect. Both ends are measured, so the guard checks membership in that range rather than a
# tolerance band around a single figure, which is what it did before and passed only because the
# oracle's 64-node rise happened to fall inside two percent of the floor.
floor, ceiling = counts["collected_nop"], counts["collected_oracle"]
MARGIN = 16  # unmeasured parametrisation slack; both endpoints above are exact and deterministic
cases = list(ET.parse(report).iter("testcase"))
seen = len(cases)
print(f"verifier: collected={seen} range=[{floor},{ceiling}] margin={MARGIN}")
if seen < floor - MARGIN:
    print(f"verifier: collected {seen} is below the no-op floor {floor}: tests went missing, refusing",
          file=sys.stderr)
    sys.exit(1)
if seen > ceiling + MARGIN:
    print(f"verifier: collected {seen} exceeds the oracle ceiling {ceiling}: the tree under test is "
          "not the tree the sets were derived from, refusing", file=sys.stderr)
    sys.exit(1)
GUARD
GUARD_RC=$?
echo "verifier: node_count_guard=$GUARD_RC"
[ "$GUARD_RC" -eq 0 ] || exit 1

# ---------------------------------------------------------------------------------------------
# 3c. final.diff, the evidence every judge.toml criterion names. The diff is the submitted package
#     tree against the pristine base-revision bytes baked into this image. A rubric whose evidence
#     has no producer is documentation rather than a channel, so this file is mandatory.
#
#     The test subtrees are excluded: they are overwritten wholesale by the overlay, so a diff of
#     them describes the overlay rather than the solver's work.
# ---------------------------------------------------------------------------------------------
mkdir -p /logs/verifier
diff -ruN \
  --exclude='__pycache__' --exclude='*.pyc' --exclude='tests' \
  /opt/pristine/networkx "$WORK/networkx" \
  > /logs/verifier/final.diff 2>/dev/null
echo "verifier: final_diff_bytes=$(wc -c < /logs/verifier/final.diff | tr -d ' ')"

# Reward Kit needs the report and the edit count where the scorer expects them.
cp -f "$STATE/junit.xml" /logs/verifier/junit.xml 2>/dev/null
cp -f "$STATE/test_edit_count" /logs/verifier/test_edit_count 2>/dev/null

# ---------------------------------------------------------------------------------------------
# 4b. CTRF projection of the same report. gold_subset.py joins a gold-subset capture to this
#     bundle's tests/cheat-checks.json on CTRF `name`, so the names here must be the same
#     path-form node ids sets.json carries. The classname-to-path resolution therefore probes the
#     same roots, authoritative first, that tests/test_output.py probes: a dotted classname has no
#     marker separating module from class, so the filesystem decides and a heuristic would guess.
#     Only `name` and `status` are read downstream; no other CTRF field is evidence.
# ---------------------------------------------------------------------------------------------
python - "$STATE/junit.xml" /logs/verifier/ctrf.json <<'CTRF'
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

source, destination = Path(sys.argv[1]), Path(sys.argv[2])
TREES = tuple(
    Path(root) for root in ("/opt/authoritative/overlay", "/app") if Path(root).is_dir()
)


def node_id(classname: str, name: str) -> str:
    parts = classname.split(".")
    for index in range(len(parts), 0, -1):
        candidate = Path(*parts[:index]).with_suffix(".py")
        if any((tree / candidate).is_file() for tree in TREES):
            inner = "::".join(parts[index:])
            return f"{candidate.as_posix()}::{inner + '::' if inner else ''}{name}"
    return f"{classname}::{name}"


tests, seen = [], set()
try:
    root = ET.parse(source).getroot()
except (OSError, ET.ParseError):
    root = None
if root is not None:
    for case in root.iter("testcase"):
        classname = case.get("classname") or ""
        if not classname:
            continue
        if case.find("failure") is not None:
            status = "failed"
        elif case.find("error") is not None:
            status = "failed"
        elif case.find("skipped") is not None:
            status = "skipped"
        else:
            status = "passed"
        identity = node_id(classname, case.get("name") or "")
        if identity in seen:
            continue
        seen.add(identity)
        tests.append({"name": identity, "status": status})
report = {
    "results": {
        "tool": {"name": "pytest"},
        "summary": {
            "tests": len(tests),
            "passed": sum(1 for item in tests if item["status"] == "passed"),
            "failed": sum(1 for item in tests if item["status"] == "failed"),
            "skipped": sum(1 for item in tests if item["status"] == "skipped"),
        },
        "tests": tests,
    }
}
destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(f"verifier: ctrf_tests={len(tests)}")
CTRF

# ---------------------------------------------------------------------------------------------
# 4. Hand scoring to Reward Kit. It reads its criteria and scoring config from /tests and writes
#    /logs/verifier/reward.json, attributing every zero to a machine-readable reason.
# ---------------------------------------------------------------------------------------------
cd /tests || exit 1
# The judge is reached through OPENAI_BASE_URL and OPENAI_API_KEY from [verifier.env]. It gets up
# to three attempts so one transient error (a 429, a 5xx, a dropped connection) does not cost the
# run its reward. An attempt counts only when Reward Kit exits 0 and no judged criterion carries an
# error, because a judge timeout is recorded as an errored 0 rather than raised. With no key, or no
# complete judge result after three attempts, the reward is the deterministic channel alone and
# judge_unavailable records why: before this, an unreachable judge left no reward.json at all.
LOG_DIR=/logs/verifier
judged_ok=0
if [ -n "${OPENAI_API_KEY:-}" ]; then
  for judge_attempt in 1 2 3; do
    rm -f "$LOG_DIR/reward.json" "$LOG_DIR/reward-details.json"
    if rewardkit /tests && [ -s "$LOG_DIR/reward.json" ] && python3 - "$LOG_DIR/reward-details.json" <<'JUDGED'
import json
import sys


def judge_criteria(node):
    if isinstance(node, dict):
        if node.get("name") == "judge" and isinstance(node.get("detail"), dict):
            yield from node["detail"].get("criteria") or []
        for value in node.values():
            yield from judge_criteria(value)
    elif isinstance(node, list):
        for value in node:
            yield from judge_criteria(value)


criteria = list(judge_criteria(json.load(open(sys.argv[1], encoding="utf-8"))))
sys.exit(0 if criteria and not any(c.get("error") for c in criteria) else 1)
JUDGED
    then
      judged_ok=1
      break
    fi
    echo "verifier: judge attempt $judge_attempt returned no complete result" >&2
    [ "$judge_attempt" -lt 3 ] && sleep $((20 * judge_attempt))
  done
fi
if [ "$judged_ok" = 1 ]; then
  rewardkit_status=0
else
  [ -f "$LOG_DIR/reward-details.json" ] && mv -f "$LOG_DIR/reward-details.json" "$LOG_DIR/judge-details.json"
  rm -f "$LOG_DIR/reward.json"
  echo "the LLM judge returned no result; the reward is the deterministic channel alone" \
    > "$LOG_DIR/judge_unavailable"
  # Written into the private state directory at verify time, so the image gains no file and
  # tests/.dockerignore needs no new entry. test_output.py is a symlink so the scorer still resolves
  # sets.json and its other inputs from /tests.
  NOJUDGE="$STATE/nojudge"
  mkdir -p "$NOJUDGE"
  ln -s /tests/test_output.py "$NOJUDGE/test_output.py"
  printf '%s\n' '[[reward]]' 'name = "reward"' 'aggregation = "weighted-mean"' \
    'weights = { test_output = 1.0 }' '' '[scoring.test_output]' 'aggregation = "weighted-mean"' \
    > "$NOJUDGE/reward.toml"
  rewardkit "$NOJUDGE"
  rewardkit_status=$?
  echo "verifier: judge unavailable, deterministic channel alone (rewardkit exit=$rewardkit_status)"
fi

# A red line must zero the WHOLE score. Reward Kit scores test_output and judge as siblings under
# weighted-mean, so the gate every criterion in test_output.py carries cannot reach the judged
# tenth: a measured run that edited twelve graded test files banked 0.1 with its deterministic
# channel already zeroed. Reward Kit offers no multiplicative aggregation, and min would discard
# the 90/10 split delivery binds, so the override is applied here. It calls the scorer's own
# _gates() rather than restating the red lines, so the two can never drift apart.
python3 - <<'REDLINE'
import json
import pathlib
import sys

sys.path.insert(0, "/tests")
import test_output as scorer

gate = scorer._gates()
if gate == 1.0:
    print("verifier: red line clear, composed reward stands")
    raise SystemExit(0)

reason = scorer._gate_reason() or "red-line"
target = pathlib.Path("/logs/verifier/reward.json")
try:
    composed = json.loads(target.read_text(encoding="utf-8"))
except OSError:
    print("verifier: no reward.json to override", file=sys.stderr)
    raise SystemExit(0)
before = composed.get("reward")
# Harbor parses every value in reward.json as a reward figure, so this file stays strictly
# numeric: a sibling key carrying the reason raised VerifierOutputParseError. The explanation
# goes beside it instead, where it is still shipped as evidence.
composed["reward"] = 0.0
target.write_text(json.dumps(composed, indent=2) + "\n", encoding="utf-8")
pathlib.Path("/logs/verifier/red_line.json").write_text(
    json.dumps(
        {
            "reason": reason,
            "composed_before_override": before,
            "note": (
                "Reward Kit composes test_output and judge as siblings under weighted-mean, so "
                "the gate every criterion in test_output.py carries cannot reach the judged "
                "component. The composed reward is zeroed here instead."
            ),
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
print(f"verifier: red line {reason} zeroed the composed reward (was {before})")
REDLINE

exit "${rewardkit_status}"
