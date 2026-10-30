"""GENERATED SECTION. DO NOT HAND-EDIT.

Generated file. Every criterion below is registered under its rubric item id with that item's
weight. Reward Kit imports this file during discovery, so nothing here acts on import beyond
registering criteria: the suite runs lazily, once, on the first criterion that needs it.

An unreadable report is total: every criterion fails closed rather than passing by default.
"""

from __future__ import annotations

import functools
import json
import math
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import rewardkit as rk
from rewardkit import criterion

TESTS = Path(__file__).resolve().parent
SETS = json.loads((TESTS / "sets.json").read_text(encoding="utf-8"))
REQUIRED_TOTAL = len(SETS["required_to_pass"])
BASELINE = json.loads((TESTS / "baseline_manifest.json").read_text(encoding="utf-8"))["status"]
GROUP_MAP = json.loads((TESTS / "group_map.json").read_text(encoding="utf-8"))
GROUPS = {group: rows["nodes"] for group, rows in GROUP_MAP["groups"].items()}
WEIGHTS = {group: rows["weight"] for group, rows in GROUP_MAP["groups"].items()}
WORKSPACE = Path(os.environ.get("REWARDKIT_WORKSPACE", "/app"))
STATE = Path(os.environ.get("VERIFIER_STATE", "/tmp"))
JUNIT = STATE / "junit.xml"
TESTS_MODIFIED_FLAG = STATE / "tests_modified"


def _node_id(tree: Path, classname: str, name: str) -> str:
    # The predeclared sets record a node as the dotted module path pytest's junit writer already
    # emits as `classname`, so the id is that verbatim. Resolving the dotted path to a file and
    # rebuilding a slash-separated id, as a path-form set would need, matches nothing here and
    # silently resolves zero required nodes while every gate still reports as if it had run.
    del tree
    return f"{classname}::{name}"


@functools.lru_cache(maxsize=1)
def _outcomes() -> dict[str, str] | None:
    """Parse the report tests/test.sh produced. None means the report could not be read at all."""
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
        seen[_node_id(WORKSPACE, classname, case.get("name") or "")] = status
    return seen


@functools.lru_cache(maxsize=1)
def _report_readable() -> bool:
    """An unreadable report fails every criterion that depends on it. It never reaches a pass."""
    return _outcomes() is not None


@functools.lru_cache(maxsize=1)
def _required_unresolved() -> int:
    seen = _outcomes()
    if seen is None:
        return len(SETS["required_to_pass"])
    return sum(1 for node in SETS["required_to_pass"] if seen.get(node) != "passed")


@functools.lru_cache(maxsize=1)
def _must_keep_regressed() -> int:
    """Regression against the recorded baseline, never against bare not-passed.

    A node counts as regressed only when the baseline manifest recorded it passing at the
    base revision and this run reports it not-passed. A node the manifest did not record
    as passing cannot regress, so a host-dependent platform guard that skips is neutral
    rather than damage attributed to the solver.
    """
    seen = _outcomes()
    was_passing = [n for n in SETS["must_keep_passing"] if BASELINE.get(n) == "passed"]
    if seen is None:
        return len(was_passing)
    return sum(1 for node in was_passing if seen.get(node) != "passed")


@functools.lru_cache(maxsize=1)
def _tests_modified() -> int:
    """Red-line state, captured by tests/test.sh before the authoritative tree was restored.

    Returns 0 when the graded tree matched the bytes the image shipped, 1 when it did not, and
    -1 when the flag could not be read. Only 0 clears the red line, so an unreadable flag fails
    closed rather than resolving to either a clean or a dirty tree.
    """
    try:
        raw = TESTS_MODIFIED_FLAG.read_text(encoding="utf-8").strip()
    except OSError:
        return -1
    return 1 if raw != "0" else 0


@functools.lru_cache(maxsize=1)
def _red_lines_hold() -> bool:
    """RL-NO-TEST-EDIT is the only red line a criterion can assert from graded state.

    RL-NO-GOLD-LIFT is enforced structurally, and RL-NO-NETWORK is scoped. network_mode is
    "no-network" on the environment, and "allowlist" over two private host-gateway ranges on
    both verifier planes, because the judged channel is a Reward Kit judge inside the verifier
    and a judge with no route to a model cannot grade. No plane reaches a public address, so
    the upstream answer is unfetchable, but this grading phase does reach a model bridge on the
    host and that is deliberate rather than structural. The agent phase runs under an
    allowlist of private
    host-gateway ranges, since an agent with no route to a model cannot act; it holds no
    provider credential and reaches no public address, and the image destroyed its git
    metadata, so the upstream answer is unfetchable from either phase.
    RL-NO-REGRESSION is carried by its own two items. A tripped red line zeroes every
    criterion here, so the weighted mean is zero and the catastrophic penalty survives
    continuous aggregation rather than shaving a single weight.
    """
    return _tests_modified() == 0


@functools.lru_cache(maxsize=1)
def _gradable() -> bool:
    """Evidence validity shared by every criterion, extending the fail-closed rule.

    An unreadable report or a tripped red line is total: no criterion reaches a pass
    on evidence that is absent or inadmissible.
    """
    return _red_lines_hold() and _report_readable()


@functools.lru_cache(maxsize=1)
def _special_cased() -> bool:
    """The required set resolving while the existing suite breaks, in one run.

    That joint outcome is the gaming pattern RB-ROBUSTNESS-NO-SPECIAL-CASE names, and
    it is what separates it from the plain regression obligation: a regression alone is
    RB-CONSTRAINTS-NO-REGRESS, whereas a regression bought by passing the required set
    is this item.
    """
    return _required_unresolved() == 0 and _must_keep_regressed() > 0


@functools.lru_cache(maxsize=1)
def _repaired() -> int:
    """Required-to-pass members now passing. Item 10g proves the base tree repairs none."""
    return 0 if not _report_readable() else REQUIRED_TOTAL - _required_unresolved()


@functools.lru_cache(maxsize=1)
def _group_completion() -> dict:
    """Completion fraction per feature group, fail-closed on a node absent from the report.

    Grouping is per feature, never per node. Without it a group holding 52 parametrisations
    of one six-line helper outweighs seven other features combined, and the gradient points
    at the cheapest file rather than at the specification.
    """
    seen = _outcomes() or {}
    out = {}
    for group, nodes in GROUPS.items():
        passed = sum(1 for node in nodes if seen.get(node) == "passed")
        out[group] = passed / len(nodes) if nodes else 0.0
    return out


@functools.lru_cache(maxsize=1)
def _depth() -> float:
    """Weighted mean completion across groups: the gradient inside a feature."""
    done = _group_completion()
    return sum(WEIGHTS[g] * done[g] for g in GROUPS)


@functools.lru_cache(maxsize=1)
def _breadth() -> float:
    """Weighted count of groups finished whole: this is what rewards finishing a feature."""
    done = _group_completion()
    return sum(WEIGHTS[g] for g in GROUPS if done[g] >= 1.0)


@functools.lru_cache(maxsize=1)
def _outcome() -> float:
    """Work accomplished. Every additive term in the reward lives here and nowhere else."""
    return 0.70 * _depth() + 0.30 * _breadth()


@functools.lru_cache(maxsize=1)
def _regression_denominator() -> int:
    """Graduated-regression denominator, also the catastrophic ceiling R_max."""
    return max(20, math.ceil(0.01 * len(SETS["must_keep_passing"])))


@functools.lru_cache(maxsize=1)
def _regression_factor() -> float:
    """Regression is a graduated multiplier, never an additive term and never a cliff.

    One incidental regression in a 1571-node preserve suite should cost a proportion of
    the reward, not all of it; R at or above the denominator is catastrophic and gated.
    """
    return max(0.0, 1.0 - _must_keep_regressed() / _regression_denominator())


@functools.lru_cache(maxsize=1)
def _gate_reason() -> str | None:
    """The first red line that zeroes the reward multiplicatively, or None."""
    if not _report_readable():
        return "G1-evidence-unreadable"
    if _tests_modified() > 0:
        return "G3-graded-test-modified"
    if _must_keep_regressed() >= _regression_denominator():
        return "G5-catastrophic-regression"
    return None


@functools.lru_cache(maxsize=1)
def _gates() -> float:
    """Product of the 0/1 red-line gates. A gate never contributes additive credit."""
    return 0.0 if _gate_reason() is not None else 1.0


@functools.lru_cache(maxsize=1)
def _score_eval() -> float:
    """The single composed reward value.

    Reward Kit's weighted mean cannot express a product, so the gate-times-term
    composition is computed here and every criterion reports it. The rubric weights stay
    the audit-facing record of what each item is worth; the arithmetic weighting that
    decides the reward is WEIGHTS, per feature group.

    The judged quality channel is absent from this bundle, so the process term is absent
    rather than zero: a missing channel must never be scored as a model failure.
    """
    return _gates() * _outcome() * _regression_factor()


@functools.lru_cache(maxsize=1)
def _score_binary() -> float:
    """Binary resolution: every group whole and not one regression."""
    done = _group_completion()
    whole = all(done[g] >= 1.0 for g in GROUPS)
    return _gates() * (1.0 if whole and _must_keep_regressed() == 0 else 0.0)


def _graded(own: bool, violation: str) -> dict:
    """Score is the composed reward; reasoning always reports this item's own verdict.

    A zero is never a claim that this item's judgment failed. The no-op's test tree really
    is byte-identical, and the record says so while the score reflects work accomplished.
    """
    reason = violation if not own else (_gate_reason() or "")
    return {"score": _score_eval(), "reasoning": reason}


@functools.lru_cache(maxsize=1)
def _fix_rate() -> float:
    """Retained for TRUTH.md's reference ladder; the carrier value comes from _coverage()."""
    if not _gradable() or _must_keep_regressed() > 0:
        return 0.0
    total = len(SETS["required_to_pass"])
    if total == 0:
        return 0.0
    return (total - _required_unresolved()) / total


@criterion(description='RB-OUTCOME-IMPL')
def rb_outcome_impl(workspace: Path) -> dict:
    return _graded(_report_readable() and _required_unresolved() == 0,
                   f"unresolved:{_required_unresolved()}")


@criterion(description='RB-COVERAGE-REQUIRED')
def rb_coverage_required(workspace: Path) -> dict:
    return _graded(_report_readable() and _required_unresolved() == 0,
                   f"incomplete:{_required_unresolved()}")


@criterion(description='RB-CONSTRAINTS-NO-REGRESS')
def rb_constraints_no_regress(workspace: Path) -> dict:
    return _graded(_report_readable() and _must_keep_regressed() == 0,
                   f"regressed:{_must_keep_regressed()}")


@criterion(description='RB-CONSTRAINTS-NO-TEST-EDIT')
def rb_constraints_no_test_edit(workspace: Path) -> dict:
    return _graded(_tests_modified() == 0,
                   "test-tree-modified" if _tests_modified() > 0 else "flag-unreadable")


@criterion(description='RB-ROBUSTNESS-NO-SPECIAL-CASE')
def rb_robustness_no_special_case(workspace: Path) -> dict:
    return _graded(_report_readable() and not _special_cased(), "special-cased")


# Registration. Reward Kit scores a criterion only once it is called.
rk.rb_outcome_impl(weight=5.0)
rk.rb_coverage_required(weight=5.0)
rk.rb_constraints_no_regress(weight=5.0)
rk.rb_constraints_no_test_edit(weight=5.0)
rk.rb_robustness_no_special_case(weight=3.0)
