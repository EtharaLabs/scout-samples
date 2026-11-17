# Evolve maximum flow, connectivity cuts and centrality

The repository is pinned at a revision that predates a later release. Your task is to make the
behaviour that release describes appear, without regressing behaviour the pinned revision already provides. The
objectives below are the release's own scope restated. They are numbered for reference only.

You are not given the release tag, any pull request number, or any diff. Derive the change list from
the objectives and the repository.

**This task is mostly behaviour change behind interfaces that already exist.** Only one new symbol
is disclosed below. For everything else the callables are already exported by the pinned
revision, so you cannot work from a signature: you must read how the surrounding module behaves and
how its callers use it.

## Disclosed interfaces

Every symbol below is created by this release and appears nowhere in the source tree you
received, so no amount of reading could recover its name. Each is referenced by the exact name and
arity given: correct behaviour behind a different name or arity does not satisfy them. Symbols this
release changes that ALREADY exist in your tree are deliberately not listed; find those yourself.
A name on its own is not enough: each symbol must carry the behaviour described below.

| Module | Symbol | Parameters | Returns |
| --- | --- | --- | --- |
| `networkx.algorithms.flow.utils` | `_capacity_function` | G, capacity | a callable resolving an edge's capacity. PRIVATE but required: it is referenced by name. When `capacity` is already callable it is returned unchanged, and such a callable must accept exactly three positional arguments (u, v, edge_attrs) and return either None to hide the edge or a number. When `capacity` is a string it names an edge attribute and a new callable is built around it. MultiGraph and MultiDiGraph are not supported. |

## Objectives

**1. One way to read an edge's capacity.** Every maximum-flow algorithm in the package resolves edge
capacity for itself, each with its own handling of a missing attribute. Replace that with a single
accessor the flow algorithms share. It takes the graph and a capacity specifier. When the specifier
is already a callable it is handed back untouched, and such a callable receives an edge's two
endpoints and that edge's attribute dictionary, returning either a number or a signal that the edge
is to be ignored entirely. When the specifier is a string it names an edge attribute, and the
accessor builds the equivalent callable around it. Multigraphs are out of scope and must be
rejected. Thread this accessor through the flow algorithms so capacity resolution stops being
duplicated per algorithm.

**2. A cutoff that cannot be honoured is reported.** The maximum-flow entry point accepts a cutoff
that stops the search early once the flow value reaches it, and it also accepts an explicitly chosen
flow function. Not every flow function can honour a cutoff. Where the caller asks for both and the
combination is impossible, the entry point must say so rather than accept the argument and discard
it. Decide which function that is from the algorithms themselves, and document the restriction where
the parameter is described.

**3. Minimum cuts are computed from the flow they correspond to.** The connectivity cut routines
return a partition of the nodes. Correct and extend them so the partition they report is the one the
underlying maximum flow actually induces, including for graphs where the residual network leaves the
choice of side ambiguous, and including the trivial and disconnected cases.

**4. Closeness centrality handles the graphs that break the naive formula.** Correct closeness
centrality for the cases the simple reciprocal-of-distance-sum formula gets wrong: nodes that reach
nothing, components smaller than the graph, and the choice of whether to normalise by the reachable
set or the whole graph. The existing arguments keep their names and meanings.

**5. Group betweenness is computed over the group, not per member.** Group betweenness centrality
asks how much shortest-path flow passes through a *set* of nodes. Correct it so the measure is taken
over the group as a whole rather than aggregated from single-node values, and so it behaves for
overlapping groups, for a group covering the whole graph, and for the weighted case.

**6. Current-flow closeness and k-components follow their definitions.** Correct current-flow
closeness centrality so it derives from the graph's Laplacian rather than from a shortest-path
approximation, and correct the k-components routine so the components it reports satisfy the
connectivity threshold it was asked for.

Objectives 1 and 2 reshape how the flow stack is parameterised. Objectives 3 through 6 correct
behaviour behind unchanged signatures.

## Constraints

Change only library source under `networkx/`. Do not modify any `tests/` directory.

Complete objectives rather than spreading partial repairs across all of them. A change that
satisfies one objective by breaking another is not an improvement.

One module cannot be imported against the pinned revision at all, because it names the accessor of
objective 1. Until that accessor exists, nothing in that module can run.
