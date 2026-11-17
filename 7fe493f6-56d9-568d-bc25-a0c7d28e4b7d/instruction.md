# Evolve the core graph views, serialisation, spectra and generators

The repository is pinned at a revision that predates a later release. Your task is to make the
behaviour that release describes appear, without regressing the 7855 tests that already pass. The
objectives below are the release's own scope restated. They are numbered for reference only.

You are not given the release tag, any pull request number, or any diff. Derive the change list from
the objectives and the repository.

**This task is broad rather than deep.** The work spans 27 files and 42 behavioural areas, and no
single area dominates. There is no single insight that carries it; there are seven mostly
independent pieces of work. The disclosed-interfaces table below names six new public symbols,
because the suite reaches them through the package namespace and a name this release invents is pure
convention rather than something the tree implies. Objectives 1, 2 and 7 change conduct behind
interfaces that already exist, and for those you must read what the tests assert.

## Disclosed interfaces

Every symbol below is created by this release and appears nowhere in the source tree you
received, so no amount of reading could recover its name. The suite imports each exactly as
written: correct behaviour behind a different name or arity does not satisfy them. Symbols this
release changes that ALREADY exist in your tree are deliberately not listed; find those yourself.
A name on its own is not enough: each symbol must carry the behaviour described below.

| Module | Symbol | Parameters | Returns |
| --- | --- | --- | --- |
| `networkx.algorithms.dag` | `antichain_width` | G | the width of the partial order the DAG defines, that is the largest number of mutually incomparable nodes. Takes the graph alone: no keyword arguments. |
| `networkx.algorithms.walks` | `random_walk` | G, *, start, weight=None, seed=None | a generator yielding the nodes a random walk visits, beginning at `start`. Note `start` is KEYWORD-ONLY and REQUIRED, so a positional call is a TypeError. `weight` names an edge attribute biasing the step choice and `seed` makes the walk reproducible. |
| `networkx.linalg.laplacianmatrix` | `magnetic_laplacian_matrix` | G, *, nodelist=None, normalized=False, q=0.25, weight="weight" | the magnetic Laplacian, a Hermitian matrix whose off-diagonal entries carry a phase set by `q`. Every argument after the graph is KEYWORD-ONLY, and the default phase is 0.25 rather than zero. |
| `networkx.linalg.spectrum` | `magnetic_spectrum` | G, *, q=0.25, weight="weight", normalized=False | the eigenvalues of that magnetic Laplacian. Keyword-only after the graph, with the same 0.25 default phase. Note the argument ORDER differs from magnetic_laplacian_matrix, which is harmless because both are keyword-only. |
| `networkx.generators.random_graphs` | `random_k_lift` | G, k, seed=None | a k-lift of G: the result holds k copies of every node, and each edge of G becomes a random perfect matching between the two endpoint fibres. `k` is POSITIONAL, unlike the keyword-only style of the matrix constructors above. |
| `networkx.generators.small` | `shrikhande_graph` | create_using=None | the Shrikhande graph, a 4-by-4 toroidal grid with the diagonal wraparound connections that make it strongly regular. Follows the convention of its neighbours in the small-graph module, taking only `create_using`. |

## Objectives

**1. The view classes stop holding their graph alive.** The node, edge and degree views each keep a
reference to the graph they report on. Change that to a weak reference, so a view cannot by itself
prevent a graph from being collected, and make the views behave sanely once the graph is gone rather
than raising an obscure error from deep inside an attribute lookup. The same change must leave the
views picklable: a view that holds a weak reference cannot be serialised naively, so provide
explicit pickling support that reconstructs the view against its graph on load. Node-bunch iteration
moves out of the graph class and into a helper the views share.

**2. GEXF reading survives the files it is given.** The GEXF reader builds a graph from parsed XML.
Rework it so graph construction is a separate step from parsing, so that the attributes declared in
a file's metadata are applied consistently, and so that a file whose declarations are incomplete or
out of order is read rather than rejected. The writer must keep producing files the reader accepts.

**3. Walks on a graph.** Add a generator that performs a random walk from a given start node,
yielding the nodes it visits, optionally biasing each step by an edge attribute and optionally
seeded for reproducibility. Extend the existing walk-counting machinery alongside it so the two
agree about what constitutes a step.

**4. The width of a partial order.** A directed acyclic graph defines a partial order. Add a measure
of that order's width: the largest set of nodes none of which reaches any other. Extend the
surrounding DAG machinery as the measure requires.

**5. Random constructions over an existing graph.** Add a lift construction: given a graph and an
integer, produce a graph holding that many copies of each original node, with each original edge
realised as a random perfect matching between the two endpoint fibres. It is seedable.

**6. Spectral matrices that carry a phase.** Add a Laplacian variant whose off-diagonal entries
carry a complex phase controlled by a parameter, together with a companion returning that matrix's
eigenvalues. Both default the phase to a non-zero value, both accept an optional node ordering and
weight attribute, and both normalise on request. These are new interfaces: choose the argument
boundaries to match the signatures in the disclosed-interfaces table exactly.

**7. A named graph, and the helpers around it.** Add the Shrikhande graph to the small-graph
collection, following the conventions of its neighbours there. Correct the adjacency and incidence
matrix constructors, the graph helper functions, the distance measures, and planarity checking, in
each case so that the behaviour the tests assert holds for the degenerate inputs the current code
mishandles.

Objectives 3, 4, 5 and 6 add capability. Objectives 1, 2 and 7 change behaviour behind interfaces
that already exist.

One coupling is worth stating, because inferring it costs a working import. The distance measures of
objective 7 share a dispatch name with a function in the tree-algorithms package. If you add the new
measure without reconciling that other definition, the dispatch registry rejects the duplicate and
`import networkx` fails outright.

## Constraints

Change only files under `networkx/`. Do not modify files under any `tests/` directory; those are
restored from the release before your work is exercised, so edits to them have no effect.

Complete objectives rather than spreading partial repairs across all of them. A change that
satisfies one objective by breaking another is not an improvement.
