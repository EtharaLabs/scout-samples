#!/bin/bash
# Reference solution for the networkx release-evolution task.

#
# The patch is confined to non-test sources under networkx/algorithms/flow,
# networkx/algorithms/connectivity and networkx/algorithms/centrality. It touches no test file,
# because the verifier restores every test
# subtree from the target revision before grading and a test edit could not change a score anyway.
#
# This patch adds no module and deletes none: every hunk changes behaviour behind a callable the
# pinned revision already exports, except the one private accessor in flow/utils.py.
set -euo pipefail

cd "${1:-/app}"

if [ ! -d networkx ]; then
  echo "solve: no networkx package tree at $(pwd), refusing" >&2
  exit 1
fi

PATCH="$(dirname "$(readlink -f "$0")")/fix.patch"
if [ ! -f "$PATCH" ]; then
  echo "solve: fix.patch not found beside this script" >&2
  exit 1
fi

# -p1 strips the leading path component the diff carries. --forward refuses an already-applied
# patch rather than reversing it, so a double invocation fails loudly instead of silently undoing
# the work.
#
# --remove-empty-files is required for the kernighan_lin.py deletion: a unified diff represents a
# removed file as a hunk that empties it, and without this flag patch leaves a zero-byte module that
# still imports.
patch -p1 --forward --batch --remove-empty-files < "$PATCH"

# Fail closed if the patch did not produce the behaviour the task requires. A patch that applies
# with fuzz and lands the wrong content would otherwise reach the grader as a plausible submission.
grep -q 'def _capacity_function' networkx/algorithms/flow/utils.py
# The only call site is in utils.py as well, inside build_residual_network; maxflow.py never
# references the helper.
grep -q '= _capacity_function(' networkx/algorithms/flow/utils.py
test -f networkx/algorithms/connectivity/cuts.py
test -f networkx/algorithms/centrality/group.py
test -f networkx/algorithms/centrality/current_flow_closeness.py



echo "solve: reference patch applied and verified"
