# Evolve community structure and bipartite analysis

The repository is pinned at a revision that predates a later release. Your task is to make
the behaviour that release describes appear, without regressing behaviour that already
works. The objectives below are the release's own scope restated. They are numbered for
reference only; the numbering carries no order of work and no weighting.

You are not given the release tag, any pull request number, or any diff. Derive the change
list from the objectives and the repository.

## Disclosed interfaces

Every symbol below is created by this release and appears nowhere in the source tree you
received, so no amount of reading could recover its name. The suite imports each exactly as
written: correct behaviour behind a different name or arity does not satisfy them. Symbols this
release changes that ALREADY exist in your tree are deliberately not listed; find those yourself.
A name on its own is not enough: each symbol must carry the behaviour described below.

| Module | Symbol | Parameters | Returns |
| --- | --- | --- | --- |
| `networkx.algorithms.community.leiden` | `leiden_communities` | G, *, weight="weight", resolution=1.0, max_level=None, seed=None, metric="cpm", theta=0.01 | the best node communities of G. This symbol ALREADY EXISTS at the base revision as leiden_communities(G, weight="weight", resolution=1, max_level=None |
| `networkx.algorithms.community.leiden` | `leiden_partitions` | G, *, weight="weight", resolution=1.0, max_level=None, seed=None, metric="cpm", theta=0.01 | successive partitions rather than one result, so the caller observes the optimization as it proceeds. Keyword-only on the same terms as leiden_communi |
| `networkx.algorithms.community.quality` | `constant_potts_model` | G, communities, weight="weight", node_weight="node_weight", resolution=1 | the constant Potts model quality of the partition. Note node_weight is a distinct argument from weight and is positional-or-keyword, unlike the leiden entries above. |
| `networkx.algorithms.community.quality` | `_quality_delta_cpm_undirected` | G, nodes_to_add, community, resolution, weight="weight", node_weight="node_weight" | the change in constant-Potts quality from adding nodes to a community, for an undirected graph, as E_D - resolution * n_size * comm_size where E_D is the edge weight between the added nodes and the community. PRIVATE but required: test_quality.py imports it at module scope, so until it exists NONE of that module's tests can run. Discovered by a solver rollout stalling on exactly this import. |
| `networkx.algorithms.community.quality` | `_quality_delta_cpm_directed` | G, nodes_to_add, community, resolution, weight="weight", node_weight="node_weight" | the directed counterpart, as E_D_out + E_D_in - resolution * 2 * n_size * comm_size. Note the factor of two on the null term, which the undirected form does not carry. PRIVATE but required, imported at module scope by test_quality.py. |
| `networkx.algorithms.community.quality` | `overlapping_modularity` | G, communities, *, weight="weight", resolution=1 | Shen et al.'s extended modularity EQ for a cover whose sets may overlap, as a float. Absent at the base revision. Each node's contribution is discounted by the number of communities it belongs to, so on a true partition EQ reduces to standard modularity. Raises NetworkXError when `communities` is not a valid cover of G's nodes, and NetworkXNotImplemented on a directed graph. weight and resolution are keyword-only, unlike the sibling quality.modularity. |
| `networkx.algorithms.bipartite.community` | `_bipartite_modularity_merge_delta` | G, community_a, community_b, resolution, weight="weight", *, red_degree_attr="red_degree", blue_degree_attr="blue_degree", m | the change in bipartite modularity from merging two communities. PRIVATE but required: the suite imports it by name and calls it as (G, {u}, B, 1, m=m), passing resolution positionally and m by keyword. `m` is keyword-only and has NO default, so omitting it is a TypeError. The two degree-attribute names are keyword-only with the defaults shown. None of this is derivable from prose, which is why it is disclosed here. |
| `networkx.algorithms.community.bipartitions` | `spectral_modularity_bipartition` | G | a 2-tuple of sets bipartitioning G's nodes by the spectrum of the modularity matrix B = A - k_i k_j / 2m. Nodes whose eigenvector component is negative go in one block, the rest in the other. Takes G alone: no keyword arguments, and no seed, so the result is deterministic for a given graph. Absent at the base revision and lives in the same new module as greedy_node_swap_bipartition. |
| `networkx.algorithms.community.bipartitions` | `greedy_node_swap_bipartition` | G, *, init_split=None, max_iter=10 | two communities, obtained by greedy modularity maximization over node swaps. Both tuning arguments are keyword-only. |
| `networkx.algorithms.bipartite.cluster` | `butterflies` | G, nodes=None | the number of butterflies per node, a butterfly being a complete bipartite K_{2,2} subgraph. nodes is positional-or-keyword and optional, matching the surrounding bipartite cluster functions rather than the keyword-only style of the community additions. |

## Objectives

**1. Native community detection by metric optimization.** The two entry points for this method
already exist in the pinned tree, but only as dispatch stubs: one delegates, the other raises
`NotImplementedError` and its documentation says a backend is required. Implement them natively,
so the library performs the detection itself with no backend. The algorithm moves nodes between
communities to improve a quality metric, refines the resulting partition, aggregates the graph by
those communities, and repeats until the metric stops improving or a level cap is reached. One
entry point returns the best partition found; the other yields the successive partitions so a
caller can observe the optimization rather than only its result.

The signatures also change. Both gain a `metric` argument naming the quality function to optimise and a `theta`
argument setting the randomness of the refinement phase; `leiden_partitions` also gains
`max_level`. These names are listed in the disclosed-interfaces table.
positionally. Preserving the existing arity will fail the suite even if the algorithm is correct.

**2. A partition quality measure the above can optimize.** Add the constant Potts model as
a quality function over a partition. It sums, over each community, the internal edge weight
less a resolution-scaled term in the community's node weight. It takes both an edge weight
attribute and a node weight attribute, and these are distinct.

**3. Bipartite modularity as a quality function.** Bipartite graphs need their own
modularity, because the one-mode measure assumes a single node set and is not meaningful
across a bipartition. Add Barber's bipartite modularity in a new bipartite community module.
It must be told which node set forms one side of the bipartition; this is not inferable from
the partition alone.

**4. Splitting nodes into two communities.** A new module gains two ways to cut a graph's nodes
into exactly two communities. The first is spectral: it builds the modularity matrix, takes the
eigenvector picked out by the extreme eigenvalue, and splits nodes by the sign of their component.
It takes the graph alone, with no tuning arguments and no seed, so its result is determined by the
graph. The second is greedy: it repeatedly moves the single node whose move most improves
modularity, keeping the best partition seen, and accepts an optional initial split and a cap on
iterations.

**5. Counting a bipartite clustering motif.** The bipartite clustering module gains a count,
per node, of the complete bipartite four-node subgraphs the node participates in. It accepts
an optional node subset and otherwise matches the conventions of the functions beside it.

**6. Bipartite matrix forms.** The matrix representation of a bipartite graph is corrected and
extended in its handling of node ordering, weights, dtypes, and the mapping back from matrix
indices to graph nodes. The constructors gain optional parameters naming the order of each side's
nodes, defaulting so that a call written against the pinned revision still works. Existing
parameters keep their names, order and optionality. Infer the required behaviour from the tests'
expectations and the surrounding module.

**7. Modularity for an overlapping cover.** Standard modularity assumes each node belongs to
exactly one community. Add a quality function for a *cover*, where a node may belong to several
communities at once, by discounting each node's contribution in proportion to the number of
communities containing it. On a cover that is in fact a partition the result must reduce to
standard modularity. It rejects a `communities` argument that is not a valid cover of the graph's
nodes, and rejects a directed graph, since the formulation is for undirected graphs only.

Objectives 2, 3, 4, 5 and 7 add capability. Objective 1 replaces stubs with a native
implementation and widens their signatures. Objective 6 changes behaviour behind an interface that
already exists.

Two consequences of the above fall outside any single objective and are stated here so you are not
left to infer them.

The native detection of objective 1 shares its level-building and graph-aggregation helpers with
the existing Louvain implementation. Those helpers are restructured, so Louvain's internals move
with this work, and its existing behaviour must be preserved — including that detection terminates.

The bipartitioning module of objective 4 supersedes the existing Kernighan-Lin bisection. That
module is removed and its name no longer exported from the community package. Leaving it in place
alongside the new module is not the target state.

## Bound interface

The disclosed-interfaces table below names the symbols this release invents, with their module,
exact parameter list, and return shape. Those names, arities and keyword-only boundaries are
binding: the test suite imports them as written. Implementing the correct behaviour behind a
different name or a different arity will fail tests you have functionally satisfied.

**That set is not exhaustive.** Objective 6 appears in no entry, because it changes an
interface that already exists in the repository. Any objective absent from the block requires
you to derive its interface from the repository and from what the tests assert.

## Constraints

Change only files under `networkx/`. Do not modify files under any `tests/` directory; those are
restored from the release before your work is exercised, so edits to them have no effect.

Complete objectives rather than spreading partial repairs across all of them. A change that
satisfies one objective by breaking another is not an improvement.

A community-detection routine must terminate. Against the pinned revision it does not, because the
guard it checks for does not yet exist. Required behaviour is that it terminates; a routine that
runs without bound is treated as incorrect.
