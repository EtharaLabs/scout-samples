"""Programmatic scoring for the networkx release-evolution bundle.

Reward Kit imports this file during discovery, so nothing here acts on import beyond registering
criteria: the report is parsed lazily, once, on the first criterion that needs it.

An unreadable report is total: every criterion fails closed rather than passing by default.

Composition matches the sibling dvc and conan bundles so a reviewer reads one ladder, not three:

    score = gates * outcome * regression_factor
    outcome = 0.70 * depth + 0.30 * breadth

depth is the weighted fraction of required nodes resolved per group; breadth is the weight of the
groups resolved WHOLE. Partial credit therefore exists, but finishing an objective is worth more
than scattering repairs across all of them.
"""

from __future__ import annotations

import functools
import json
import math
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import rewardkit as rk
from rewardkit import criterion

TESTS = Path(__file__).resolve().parent
SETS = json.loads((TESTS / "sets.json").read_text(encoding="utf-8"))
GROUP_MAP = json.loads((TESTS / "group_map.json").read_text(encoding="utf-8"))
BASELINE = json.loads((TESTS / "baseline_manifest.json").read_text(encoding="utf-8"))[
    "status"
]

GROUPS = {name: rows["nodes"] for name, rows in GROUP_MAP["groups"].items()}
WEIGHTS = {name: rows["weight"] for name, rows in GROUP_MAP["groups"].items()}

WORKSPACE = Path(os.environ.get("REWARDKIT_WORKSPACE", "/app"))
# The authoritative target-revision test overlay. Module paths MUST resolve against this and not
# against the workspace alone: the overlay carries 267 test modules where the base revision carries
# 265, so a target-only module cannot be resolved from /app at all. Resolved against /app only, the
# dotted classname falls through to the unresolved fallback, never matches the path-form ids in
# sets.json, and every node in such a module reads as absent. Measured consequence before this was
# fixed: 800 phantom regressions on a no-op whose diff was zero bytes, which tripped the
# catastrophic gate and would have scored the ORACLE 0.0 for the same reason, making the gate
# meaningless. The sibling conan bundle lost its oracle to the same class of bug.
OVERLAY = Path(os.environ.get("VERIFIER_OVERLAY", "/opt/authoritative/overlay"))
LOGS = Path(os.environ.get("VERIFIER_LOGS", "/logs/verifier"))
JUNIT = LOGS / "junit.xml"
TEST_EDIT_COUNT = LOGS / "test_edit_count"
FINAL_DIFF = LOGS / "final.diff"

CATASTROPHIC_REGRESSIONS = 40

# The declared graded package. Both compiled hygiene criteria below reduce entirely to a path
# prefix test and a token search over final.diff, so phase build item 10f requires them to be
# compiled criteria here rather than judged criteria in tests/judge.toml.
GRADED_PACKAGE = "networkx"

# Markers that leave an interactive debugger or a trace hook in shipped implementation source.
DEBUG_MARKERS = (
    "breakpoint(",
    "pdb.set_trace",
    "import pdb",
    "import ipdb",
    "sys.settrace(",
)



def _node_id(trees: tuple[Path, ...], classname: str, name: str) -> str:
    """Resolve a junit classname to a pytest node id by probing the trees under test.

    The module boundary is not derivable from the dotted name alone: networkx keeps tests inside
    the package, so a classname like networkx.algorithms.community.tests.test_quality.TestCoverage
    has no marker separating module from class. Walking longest-to-shortest and asking the
    filesystem is exact where a naming heuristic is a guess.

    Every tree is probed, overlay first, because a target-only test module exists in the overlay
    and not in the base-revision workspace. Probing only the workspace silently mis-resolves those
    modules; see the OVERLAY comment above for what that cost.
    """
    parts = classname.split(".")
    for i in range(len(parts), 0, -1):
        candidate = Path(*parts[:i]).with_suffix(".py")
        if any((tree / candidate).is_file() for tree in trees):
            cls = "::".join(parts[i:])
            return f"{candidate.as_posix()}::{cls + '::' if cls else ''}{name}"
    return f"{classname}::{name}"


@functools.lru_cache(maxsize=1)
def _outcomes() -> dict[str, str] | None:
    """Parse the report tests/test.sh produced. None means it could not be read at all."""
    try:
        root = ET.parse(JUNIT).getroot()
    except (OSError, ET.ParseError):
        return None
    seen: dict[str, str] = {}
    for case in root.iter("testcase"):
        classname = case.get("classname") or ""
        if not classname:
            continue
        status = "passed"
        if case.find("failure") is not None:
            status = "failed"
        elif case.find("error") is not None:
            status = "error"
        elif case.find("skipped") is not None:
            status = "skipped"
        seen[_node_id((OVERLAY, WORKSPACE), classname, case.get("name") or "")] = status
    return seen


@functools.lru_cache(maxsize=1)
def _report_readable() -> bool:
    return _outcomes() is not None


@functools.lru_cache(maxsize=1)
def _required_unresolved() -> int:
    outcomes = _outcomes()
    if outcomes is None:
        return len(SETS["required_to_pass"])
    return sum(1 for node in SETS["required_to_pass"] if outcomes.get(node) != "passed")


@functools.lru_cache(maxsize=1)
def _must_keep_regressed() -> int:
    """A must-keep node that passed at baseline and no longer passes.

    Baseline status is consulted rather than assumed: a node absent from this run's report counts
    as regressed only if the baseline recorded it passing, so a node that never existed cannot
    manufacture a regression.
    """
    outcomes = _outcomes()
    if outcomes is None:
        return len(SETS["must_keep_passing"])
    regressed = 0
    for node in SETS["must_keep_passing"]:
        if BASELINE.get(node) != "passed":
            continue
        if outcomes.get(node) not in ("passed", "skipped", "xfailed"):
            regressed += 1
    return regressed


@functools.lru_cache(maxsize=1)
def _tests_modified() -> int | None:
    """RL-NO-TEST-EDIT, counted by test.sh before the authoritative overlay was laid down.

    None means the count could not be read, which the gate treats exactly as it treats an
    unreadable report: closed. An earlier form returned 1 here, relying on one-edited-file to fire
    the red line, and that read as a returned success value to a static checker even though it was
    the punitive branch. Saying unreadable in the return type says the same thing unambiguously.
    None means the flag could not be read, which the gate treats exactly as it treats an
    unreadable report: closed. Returning a number here relied on the caller comparing it the
    right way, and a sentinel that does not satisfy that comparison fails OPEN instead.
    """
    try:
        return int(TEST_EDIT_COUNT.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


@functools.lru_cache(maxsize=1)
def _special_cased() -> bool:
    """Implementation source that names the test tree is special-casing, not engineering.

    final.diff excludes the test subtrees, so every hunk here is implementation. A hunk that
    references a test module, a test function name, or the tests package is reaching for the
    grader rather than solving the task.
    """
    try:
        diff = FINAL_DIFF.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    needles = (
        "/tests/",
        "test_leiden",
        "test_quality",
        "test_bipartitions",
        "test_community",
        "test_cluster",
        "test_matrix",
        "test_utils",
        "test_louvain",
        "PYTEST_CURRENT_TEST",
    )
    return any(n in diff for n in needles)


@functools.lru_cache(maxsize=1)
def _red_lines_hold() -> bool:
    return _tests_modified() == 0 and not _special_cased()


@functools.lru_cache(maxsize=1)
def _gradable() -> bool:
    return _report_readable() and _red_lines_hold()


@functools.lru_cache(maxsize=1)
def _group_completion() -> dict[str, float]:
    outcomes = _outcomes() or {}
    done: dict[str, float] = {}
    for name, nodes in GROUPS.items():
        if not nodes:
            done[name] = 0.0
            continue
        passed = sum(1 for node in nodes if outcomes.get(node) == "passed")
        done[name] = passed / len(nodes)
    return done


@functools.lru_cache(maxsize=1)
def _total_weight() -> float:
    """Sum of group weights, used to normalise.

    group_map.json stores each weight as 1/n rounded to five places, so for a group count that does
    not divide evenly the stored weights do not sum to exactly 1. At 31 groups the sum is 1.00006,
    and Reward Kit rounds the aggregate to four places, so a perfect submission scored 1.0001 rather
    than 1.0. Dividing by the measured total makes the rounding harmless at any group count.
    """
    return sum(WEIGHTS[g] for g in GROUPS) or 1.0


@functools.lru_cache(maxsize=1)
def _depth() -> float:
    done = _group_completion()
    return sum(WEIGHTS[g] * done[g] for g in GROUPS) / _total_weight()


@functools.lru_cache(maxsize=1)
def _breadth() -> float:
    done = _group_completion()
    return sum(WEIGHTS[g] for g in GROUPS if done[g] >= 1.0) / _total_weight()


@functools.lru_cache(maxsize=1)
def _outcome() -> float:
    return 0.70 * _depth() + 0.30 * _breadth()


@functools.lru_cache(maxsize=1)
def _regression_denominator() -> int:
    """One percent of the must-keep surface, floored at twenty.

    7855 must-keep nodes put this at 79, so a single regression costs about 1.27 percent of the
    continuous measure and 40 regressions zero it outright. The value is computed from sets.json
    rather than pinned, so correcting that set corrects this with it.
    """
    return max(20, math.ceil(0.01 * len(SETS["must_keep_passing"])))


@functools.lru_cache(maxsize=1)
def _regression_factor() -> float:
    return max(0.0, 1.0 - _must_keep_regressed() / _regression_denominator())


@functools.lru_cache(maxsize=1)
def _gate_reason() -> str | None:
    if not _report_readable():
        return "report-unreadable"
    edited = _tests_modified()
    if edited is None:
        return "test-edit-count-unreadable"
    if edited > 0:
        return f"test-tree-modified:{edited}"
    if _special_cased():
        return "special-cased"
    if _must_keep_regressed() >= CATASTROPHIC_REGRESSIONS:
        return f"catastrophic-regressions:{_must_keep_regressed()}"
    return None


@functools.lru_cache(maxsize=1)
def _gates() -> float:
    return 0.0 if _gate_reason() is not None else 1.0


@functools.lru_cache(maxsize=1)
def _score_eval() -> float:
    return _gates() * _outcome() * _regression_factor()


@functools.lru_cache(maxsize=1)
def _diff_text() -> str:
    try:
        return FINAL_DIFF.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


@functools.lru_cache(maxsize=1)
def _touched_paths() -> tuple[str, ...]:
    """Implementation paths the submission changed, as package-relative paths.

    test.sh writes final.diff with absolute container paths on both sides, so each path is cut at
    the graded package segment. A created file still carries that segment on the + side, so new
    modules are counted rather than skipped.
    """
    out: set[str] = set()
    for match in re.finditer(r"^\+\+\+ (\S+)", _diff_text(), re.MULTILINE):
        raw = match.group(1)
        if raw == "/dev/null":
            continue
        cut = raw.find("/" + GRADED_PACKAGE + "/")
        if cut >= 0:
            out.add(raw[cut + 1:])
        elif raw.startswith(("a/", "b/")):
            out.add(raw[2:])
        else:
            out.add(raw.lstrip("/"))
    return tuple(sorted(out))


@functools.lru_cache(maxsize=1)
def _added_lines() -> tuple[str, ...]:
    return tuple(
        line[1:]
        for line in _diff_text().splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


@functools.lru_cache(maxsize=1)
def _out_of_scope_paths() -> tuple[str, ...]:
    return tuple(
        p for p in _touched_paths()
        if not (p.startswith(GRADED_PACKAGE + "/") and p.endswith(".py"))
    )


@functools.lru_cache(maxsize=1)
def _debug_marker_hits() -> tuple[str, ...]:
    return tuple(
        line.strip()[:80] for line in _added_lines()
        if any(marker in line for marker in DEBUG_MARKERS)
    )


@functools.lru_cache(maxsize=1)
def _scope_paths_hold() -> bool:
    """Compound on purpose: at least one in-scope module changed AND nothing outside the package.

    The second clause alone is vacuously true of an empty diff, which would let the no-op record a
    satisfied verdict for work it never did. Requiring positive evidence first is what makes the
    recorded reasoning honest at both halves of the gate.
    """
    in_scope = [p for p in _touched_paths() if p not in _out_of_scope_paths()]
    return bool(in_scope) and not _out_of_scope_paths()


@functools.lru_cache(maxsize=1)
def _no_debug_marker() -> bool:
    """Compound for the same reason: the diff must add lines AND leave no debugger behind."""
    return bool(_added_lines()) and not _debug_marker_hits()


def _graded(own: bool, violation: str) -> dict:
    """Score is the composed reward; reasoning always reports this item's own verdict.

    A zero is never a claim that this item's judgment failed. The no-op's test tree really is
    byte-identical, and the record says so while the score reflects work accomplished.
    """
    reason = violation if not own else (_gate_reason() or "")
    return {"score": _score_eval(), "reasoning": reason}


@criterion(description="RB-OUTCOME-IMPL")
def rb_outcome_impl(workspace: Path) -> dict:
    return _graded(
        _report_readable() and _required_unresolved() == 0,
        f"unresolved:{_required_unresolved()}",
    )


@criterion(description="RB-COVERAGE-REQUIRED")
def rb_coverage_required(workspace: Path) -> dict:
    return _graded(
        _report_readable() and _required_unresolved() == 0,
        f"incomplete:{_required_unresolved()}",
    )


@criterion(description="RB-CONSTRAINTS-NO-REGRESS")
def rb_constraints_no_regress(workspace: Path) -> dict:
    return _graded(
        _report_readable() and _must_keep_regressed() == 0,
        f"regressed:{_must_keep_regressed()}",
    )


@criterion(description="RB-CONSTRAINTS-NO-TEST-EDIT")
def rb_constraints_no_test_edit(workspace: Path) -> dict:
    return _graded(
        _tests_modified() == 0,
        "test-tree-modified" if _tests_modified() > 0 else "flag-unreadable",
    )


@criterion(description="RB-ROBUSTNESS-NO-SPECIAL-CASE")
def rb_robustness_no_special_case(workspace: Path) -> dict:
    return _graded(_report_readable() and not _special_cased(), "special-cased")


@criterion(description="CM-SCOPE-PATHS")
def cm_scope_paths(workspace: Path) -> dict:
    return _graded(
        _scope_paths_hold(),
        "no-implementation-change" if not _touched_paths()
        else "out-of-scope:" + ",".join(_out_of_scope_paths()[:3]),
    )


@criterion(description="CM-NO-DEBUG-MARKER")
def cm_no_debug_marker(workspace: Path) -> dict:
    return _graded(
        _no_debug_marker(),
        "no-added-lines" if not _added_lines()
        else "debug-marker:" + " | ".join(_debug_marker_hits()[:2]),
    )


# Registration. Reward Kit scores a criterion only once it is called.
rk.rb_outcome_impl(weight=5.0)
rk.rb_coverage_required(weight=5.0)
rk.rb_constraints_no_regress(weight=5.0)
rk.rb_constraints_no_test_edit(weight=5.0)
rk.rb_robustness_no_special_case(weight=3.0)
rk.cm_scope_paths(weight=1.0)
rk.cm_no_debug_marker(weight=1.0)
