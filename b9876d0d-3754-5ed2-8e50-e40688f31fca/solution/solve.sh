#!/bin/bash
# Reference solution for the networkx release-evolution task.
#
# This applies the upstream target revision's own implementation of the seven objectives. It is the
# oracle: the bundle's gate requires that running this and then grading scores exactly 1.0, and that
# grading the unmodified tree scores exactly 0.0. Both halves were measured before delivery.
#
# The patch is confined to non-test sources under networkx/algorithms/community and
# networkx/algorithms/bipartite. It touches no test file, because the verifier restores every test
# subtree from the target revision before grading and a test edit could not change a score anyway.
#
# One hunk is a DELETION: networkx/algorithms/community/kernighan_lin.py is removed at the target
# revision, its bisection role taken over by the new community/bipartitions.py. A solver that adds
# the new module without removing the old one leaves an export that the target package no longer
# carries, so the deletion is part of the required behaviour rather than tidying.
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

# Fail closed if the patch did not produce the four symbols the task requires. A patch that applies
# with fuzz and lands the wrong content would otherwise reach the grader as a plausible submission.
test -f networkx/algorithms/community/bipartitions.py
test -f networkx/algorithms/bipartite/community.py
grep -q 'def constant_potts_model' networkx/algorithms/community/quality.py
grep -q 'def overlapping_modularity' networkx/algorithms/community/quality.py
grep -q 'def butterflies' networkx/algorithms/bipartite/cluster.py
grep -q 'def greedy_node_swap_bipartition' networkx/algorithms/community/bipartitions.py
grep -q 'def modularity' networkx/algorithms/bipartite/community.py
test ! -f networkx/algorithms/community/kernighan_lin.py

# The dispatch stub must be gone: leaving leiden_partitions raising NotImplementedError is the
# single most likely way to apply this patch and still fail every required node in test_leiden.
if grep -q "is not implemented by networkx" networkx/algorithms/community/leiden.py; then
  echo "solve: leiden_partitions still raises the backend-required stub, refusing" >&2
  exit 1
fi

echo "solve: reference patch applied and verified"
