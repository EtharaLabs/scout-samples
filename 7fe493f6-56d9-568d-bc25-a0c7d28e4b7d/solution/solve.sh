#!/bin/bash
# Reference solution for the networkx release-evolution task.
#
# This applies the upstream target revision's own implementation of the seven objectives. It is the
# oracle: the bundle's gate requires that running this and then grading scores exactly 1.0, and that
# grading the unmodified tree scores exactly 0.0. Both halves were measured before delivery.
#
# The patch is confined to non-test sources under networkx/ — algorithms, classes, generators,
# linalg and readwrite. It touches no test file, because the verifier restores every test
# subtree from the target revision before grading and a test edit could not change a score anyway.
#
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
grep -q 'def antichain_width' networkx/algorithms/dag.py
grep -q 'def random_walk' networkx/algorithms/walks.py
grep -q 'def magnetic_laplacian_matrix' networkx/linalg/laplacianmatrix.py
grep -q 'def magnetic_spectrum' networkx/linalg/spectrum.py
grep -q 'def random_k_lift' networkx/generators/random_graphs.py
grep -q 'def shrikhande_graph' networkx/generators/small.py

# The dispatch registry rejects a duplicate name, so the tree-algorithms distance module must be
# reconciled alongside the new one or `import networkx` fails outright. Prove the package imports.
PY_BIN="$(command -v python || command -v python3)"
"$PY_BIN" -c "import networkx" >/dev/null


echo "solve: reference patch applied and verified"
