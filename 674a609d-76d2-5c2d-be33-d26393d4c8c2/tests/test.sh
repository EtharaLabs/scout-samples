#!/bin/bash
# Verifier entry point for the celery release-evolution task.
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
# 1. Red line RL-NO-TEST-EDIT is STRUCTURALLY UNREACHABLE in this bundle, which is why there is
#    no comparison loop here.
#
#    This repository keeps its tests in a separate top-level t/ tree, and task.toml declares only
#    /app/celery as an artifact. The solver's t/ therefore never leaves the agent container and
#    never reaches this one: the tree graded below is this image's own pristine t/, replaced
#    wholesale at step 2 by the authoritative target-revision copy. A solver can edit, delete or
#    fabricate any test it likes and none of those bytes can touch a grade.
#
#    The three networkx siblings could not do this, because that project keeps its tests INSIDE
#    the package under grade, so their test subtrees sat within the declared artifact and had to
#    be compared byte for byte and then overwritten. Both of those mechanisms produced grading
#    defects: one nested the overlay and scored a correct oracle at 0.0, another counted a
#    conftest edit the release itself makes as a red-line violation and zeroed a rollout that had
#    resolved 161 of 187 nodes. Neither failure mode exists here.
#
#    test_edit_count is still written, because test_output.py reads it and because a reviewer
#    comparing bundles should see the same evidence file in each. Here it is 0 by construction
#    rather than by measurement, and the comment above is the justification.
# ---------------------------------------------------------------------------------------------
printf '%s\n' "0" > "$STATE/test_edit_count"
echo "verifier: test_edit_count=0 (structurally unreachable: t/ is not a declared artifact)"

# ---------------------------------------------------------------------------------------------
# 2. Grade in a fresh, verifier-owned copy. NEVER restore in place under /app.
#
#    Harbor re-materialises the declared artifact into the verifier as ROOT, while this process
#    runs as uid 10002. So every unlink under the uploaded tree is EPERM, `rm -rf` leaves the
#    directory standing, and `cp -R src dst` with dst present NESTS. Copying out instead of
#    deleting in place sidesteps the permission entirely: this uid owns $STATE, so the graded tree
#    is writable, and /app is left exactly as Harbor delivered it.
# ---------------------------------------------------------------------------------------------
GRADED="$STATE/graded"
mkdir -p "$GRADED"
cp -R "$WORK/." "$GRADED/" 2>/dev/null

# cp preserves mode, so a read-only uploaded tree arrives read-only and the replacement below
# could not overwrite it. This process owns every byte under $STATE, so chmod succeeds here where
# it would be EPERM under /app.
chmod -R u+rwX "$GRADED" 2>/dev/null

# Replace the test tree wholesale with the authoritative target-revision copy. -T is what prevents
# cp from treating an existing destination as a parent and nesting the tree at t/t/.
rm -rf "$GRADED/t"
cp -RT /opt/authoritative/t "$GRADED/t" || exit 1

# Fail closed on the nesting this step exists to prevent. A grader that silently measures the
# wrong tree is worse than one that crashes.
if [ -d "$GRADED/t/t" ]; then
  echo "verifier: test tree nested at t/t, refusing to grade" >&2
  exit 1
fi
if [ ! -f "$GRADED/t/unit/backends/test_base.py" ] || [ ! -f "$GRADED/t/unit/worker/test_native_delayed_delivery.py" ]; then
  echo "verifier: authoritative test tree missing from the graded copy, refusing to grade" >&2
  exit 1
fi
echo "verifier: graded_tree=$GRADED"

# ---------------------------------------------------------------------------------------------
# 3. Run the suite the way the upstream project runs it, identically for the real upstream
#    artifact and for a model submission.
#
#    Two backend modules are excluded because they require cloud credentials and a network this
#    verifier does not have. --timeout bounds any single node, since a broker-waiting path in this
#    project can block indefinitely rather than fail.
#
#    -o addopts= discards any addopts a transferred pytest.ini or setup.cfg would inject,
#    --confcutdir stops conftest discovery walking above the graded tree, and
#    PYTHONDONTWRITEBYTECODE keeps a stale .pyc from shadowing a replaced test.
#
#    Not yet closed: plugin autoload still runs, so a .pth, sitecustomize, or pytest11 entry point
#    in a transferred artifact executes before collection.
# ---------------------------------------------------------------------------------------------
#    -p celery.contrib.pytest is REQUIRED and is not a convenience. This project registers its
#    `celery` pytest marker from a plugin that is normally auto-loaded through the INSTALLED
#    distribution's pytest11 entry point, and pyproject.toml runs the suite with --strict-markers.
#    Neither image installs this project as a distribution, because the only versions on an index
#    are the target revision or later and shipping those bytes would hand the solver the answer.
#    Without the entry point the marker is unregistered, strict mode makes that fatal, and
#    t/unit/backends/test_base.py dies at collection taking 103 nodes with it — the exact shape of
#    the no-op, so the failure would look like a solver that did nothing. Loading the plugin
#    explicitly registers the marker from the GRADED TREE'S OWN copy, which is the submission's
#    bytes rather than an installed answer.
#    -p reap_plugin is REQUIRED for the same class of reason. Four test_AsynPool tests in
#    t/unit/concurrency/test_prefork.py build a pool and never shut it down, so each leaves
#    os.cpu_count() forks of the pytest process alive for the rest of the session. os.cpu_count()
#    does NOT observe this container's cpu limit, so the leak is sized by the HOST: 40 processes
#    holding 11.2 GB on a 10-core box, and 136 on a 34-core runner, where the cgroup was OOM-killed
#    with 98 percent of the suite done and no junit.xml written at all. No memory_mb can cover a
#    total that scales with the runner, so the workers are reaped at each teardown instead. The
#    plugin is written here rather than shipped as a file so the grading tree gains no new module.
#    It signals only this session's own non-baseline descendants, never touches the graded tree, and
#    leaves the pass/fail tally byte-identical: measured 17/3315 oracle and 67/3144 no-op either way.
mkdir -p "$STATE/plugins"
cat > "$STATE/plugins/reap_plugin.py" <<'REAP_PLUGIN'
import os
import signal
import time

_baseline = set()


def _descendants():
    me = os.getpid()
    parents = {}
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/stat", encoding="utf-8") as fh:
                stat = fh.read()
            # comm itself can contain parens, so read ppid from the LAST one.
            parents[int(entry)] = int(stat[stat.rindex(")") + 2 :].split()[1])
        except (OSError, ValueError, IndexError):
            continue
    found = set()
    for pid in parents:
        cursor = parents.get(pid) if pid != me else None
        for _ in range(64):
            if cursor is None or cursor <= 1:
                break
            if cursor == me:
                found.add(pid)
                break
            cursor = parents.get(cursor)
    return found


def pytest_sessionstart(session):
    _baseline.update(_descendants())


def pytest_runtest_teardown(item, nextitem):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        stray = _descendants() - _baseline
        if not stray:
            return
        for pid in stray:
            try:
                os.kill(pid, sig)
            except (ProcessLookupError, PermissionError):
                continue
        time.sleep(0.05)
        try:
            while os.waitpid(-1, os.WNOHANG)[0]:
                pass
        except ChildProcessError:
            pass
REAP_PLUGIN

cd "$GRADED" || exit 1
PYTHONPATH="$STATE/plugins" PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 \
python -m pytest t/unit \
  -q -p no:cacheprovider -p no:randomly --no-header \
  -o addopts= \
  -p celery.contrib.pytest \
  -p reap_plugin \
  --confcutdir="$GRADED" \
  --timeout=60 \
  --continue-on-collection-errors \
  --ignore=t/unit/backends/test_azureblockblob.py \
  --ignore=t/unit/backends/test_gcs.py \
  --junit-xml="$STATE/junit.xml"
echo "verifier: pytest exit=$?"

# ---------------------------------------------------------------------------------------------
# 3b. Exclusion guard. --ignore fails SILENTLY when a path is wrong: pytest neither warns nor
#     errors, it simply collects the module anyway, and the excluded nodes land in the report as
#     credentialless failures that look like the solver's fault. This checks by set subtraction
#     that neither excluded module contributed a node, rather than trusting the flags.
#
# 3c. Node-count guard. This bug class is otherwise invisible: a grader measuring the wrong tree
#     reports a plausible number instead of failing. The collected count must sit inside the range
#     the two graded endpoints were measured at, or the tree under test is not the tree the sets
#     were derived from.
# ---------------------------------------------------------------------------------------------
python - "$STATE/junit.xml" /tests/baseline_manifest.json <<'GUARD'
import json, sys, xml.etree.ElementTree as ET

report, manifest = sys.argv[1], sys.argv[2]
counts = json.load(open(manifest))["counts"]
cases = list(ET.parse(report).iter("testcase"))

EXCLUDED_MODULES = ("test_azureblockblob", "test_gcs")
leaked = sorted({
    c.get("classname", "")
    for c in cases
    if any(m in (c.get("classname") or "") for m in EXCLUDED_MODULES)
})
if leaked:
    print(f"verifier: --ignore did not take effect, these modules collected anyway: {leaked}",
          file=sys.stderr)
    sys.exit(1)
print(f"verifier: exclusion_guard=ok ({len(EXCLUDED_MODULES)} modules absent as intended)")

# The collected total is submission-dependent at the low end: t/unit/backends/test_base.py cannot
# be imported at the no-op, so its nodes are not collected at all, and any submission that defines
# the two private names that module imports makes them collect. Both ends are measured, so the
# guard checks membership in that range rather than a tolerance band around a single figure.
floor, ceiling = counts["collected_nop"], counts["collected_oracle"]
MARGIN = 16  # unmeasured parametrisation slack; both endpoints above are exact and deterministic
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
echo "verifier: guards=$GUARD_RC"
[ "$GUARD_RC" -eq 0 ] || exit 1

# ---------------------------------------------------------------------------------------------
# 4. final.diff, the evidence every judge.toml criterion names. The diff is the submitted package
#    tree against the pristine base-revision bytes baked into this image. A rubric whose evidence
#    has no producer is documentation rather than a channel, so this file is mandatory.
#
#    No test subtree needs excluding here: this project's tests are not inside the graded package,
#    so the diff is the solver's source work and nothing else.
# ---------------------------------------------------------------------------------------------
mkdir -p /logs/verifier
diff -ruN \
  --exclude='__pycache__' --exclude='*.pyc' \
  /opt/pristine/celery "$WORK/celery" \
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
    Path(root) for root in ("/opt/authoritative", "/app") if Path(root).is_dir()
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
# 5. Hand scoring to Reward Kit. It reads its criteria and scoring config from /tests and writes
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
