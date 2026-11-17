"""
Moody and White algorithm for k-components
"""

from collections import defaultdict
from itertools import combinations
from operator import itemgetter

import networkx as nx

# Define the default maximum flow function.
from networkx.algorithms.flow import edmonds_karp
from networkx.utils import not_implemented_for

default_flow_func = edmonds_karp

__all__ = ["k_components"]


@not_implemented_for("directed")
@nx._dispatchable
def k_components(G, flow_func=None):
    r"""Returns the k-component structure of a graph G.

    A `k`-component is a maximal subgraph of a graph G that has, at least,
    node connectivity `k`: we need to remove at least `k` nodes to break it
    into more components. `k`-components have an inherent hierarchical
    structure because they are nested in terms of connectivity: a connected
    graph can contain several 2-components, each of which can contain
    one or more 3-components, and so forth.

    Parameters
    ----------
    G : NetworkX graph

    flow_func : function
        Function to perform the underlying flow computations. Default value
        :meth:`edmonds_karp`. This function performs better in sparse graphs with
        right tailed degree distributions. :meth:`shortest_augmenting_path` will
        perform better in denser graphs.

    Returns
    -------
    k_components : dict
        Dictionary with all connectivity levels `k` in the input Graph as keys
        and a list of sets of nodes that form a k-component of level `k` as
        values.

    Raises
    ------
    NetworkXNotImplemented
        If the input graph is directed.

    Examples
    --------
    >>> # Petersen graph has 10 nodes and it is triconnected, thus all
    >>> # nodes are in a single component on all three connectivity levels
    >>> G = nx.petersen_graph()
    >>> k_components = nx.k_components(G)

    Notes
    -----
    Moody and White [1]_ (appendix A) provide an algorithm for identifying
    k-components in a graph, which is based on Kanevsky's algorithm [2]_
    for finding all minimum-size node cut-sets of a graph (implemented in
    :meth:`all_node_cuts` function):

        1. Compute node connectivity, k, of the input graph G.

        2. Identify all k-cutsets at the current level of connectivity using
           Kanevsky's algorithm.

        3. Generate new graph components based on the removal of
           these cutsets. Nodes in a cutset belong to both sides
           of the induced cut.

        4. If the graph is neither complete nor trivial, return to 1;
           else end.

    This implementation follows the same hierarchical scheme, splitting
    along one minimum node cut at a time. It relies on the fact that a
    `k`-connected subgraph cannot be split by removing fewer than `k` nodes:
    if `S` is a node cut of a subgraph `C` with `|S| < k`, every
    `k`-component inside `C` lies inside ``D | S`` for a single connected
    component `D` of ``C - S``. Thus, starting from the bicomponents of G:

        1. Restrict the current subgraph to its `(l+1)`-core, where `l` is
           the highest connectivity level already accounted for (nodes of a
           `k`-component have at least `k` neighbors in it), and process
           each of its bicomponents `C` with more than `l + 1` nodes.

        2. Compute a minimum node cut `S` of `C` (`C` is complete if it has
           none), which gives its node connectivity `k = |S|`. If `k > l`,
           `C` is a `j`-component of G for every `l < j <= k`.

        3. Recurse on ``D | S`` for each connected component `D` of
           ``C - S``, with level ``max(l, k)``.

    Every component reported at level `k` therefore has node connectivity
    at least `k`, and is maximal with that property. The heuristics of [3]_
    (cores and bicomponents) are used to prune the search.

    See also
    --------
    node_connectivity
    all_node_cuts
    biconnected_components : special case of this function when k=2
    k_edge_components : similar to this function, but uses edge-connectivity
        instead of node-connectivity

    References
    ----------
    .. [1]  Moody, J. and D. White (2003). Social cohesion and embeddedness:
            A hierarchical conception of social groups.
            American Sociological Review 68(1), 103--28.
            http://www2.asanet.org/journals/ASRFeb03MoodyWhite.pdf

    .. [2]  Kanevsky, A. (1993). Finding all minimum-size separating vertex
            sets in a graph. Networks 23(6), 533--541.
            http://onlinelibrary.wiley.com/doi/10.1002/net.3230230604/abstract

    .. [3]  Torrents, J. and F. Ferraro (2015). Structural Cohesion:
            Visualization and Heuristics for Fast Computation.
            https://arxiv.org/pdf/1503.04476v1

    """
    # Dictionary with connectivity level (k) as keys and a list of
    # sets of nodes that form a k-component as values. Note that
    # k-components can overlap (but only k - 1 nodes).
    k_components = defaultdict(list)
    # Define default flow function
    if flow_func is None:
        flow_func = default_flow_func
    # Self-loops and parallel edges do not change node connectivity.
    if G.is_multigraph() or nx.number_of_selfloops(G) > 0:
        G = nx.Graph(G)
        G.remove_edges_from(nx.selfloop_edges(G))
    # Bicomponents as a base to check for higher order k-components
    for component in nx.connected_components(G):
        # isolated nodes have connectivity 0
        comp = set(component)
        if len(comp) > 1:
            k_components[1].append(comp)
    bicomponents = [set(c) for c in nx.biconnected_components(G)]
    for bicomp in bicomponents:
        # avoid considering dyads as bicomponents
        if len(bicomp) > 2:
            k_components[2].append(bicomp)

    # Perform cuts in a DFS like order. Each entry of the stack is a set of
    # nodes and a level such that, for every k > level, any k-component of G
    # sharing more than `level` nodes with the set lies inside it.
    stack = [(bicomp, 2) for bicomp in bicomponents if len(bicomp) > 3]
    while stack:
        nodes, level = stack.pop()
        # Nodes of a k-component have at least k neighbors inside it.
        core = nx.k_core(G.subgraph(nodes), level + 1)
        # A k-component with k > level > 1 is biconnected, so it lies inside
        # one of the bicomponents of the core, and has at least k + 1 nodes.
        for block in nx.biconnected_components(core):
            if len(block) <= level + 1:
                continue
            C = G.subgraph(block)
            if C.number_of_edges() == len(C) * (len(C) - 1) // 2:
                # A complete graph has no node cut.
                cut = None
                k = len(C) - 1
            else:
                cut = nx.minimum_node_cut(C, flow_func=flow_func)
                k = len(cut)
            # C is j-connected for level < j <= k. The j-component of G that
            # contains C lies inside the nodes of this entry, hence inside the
            # core and inside its bicomponent C: C is that j-component.
            for j in range(level + 1, k + 1):
                k_components[j].append(set(block))
            if cut is not None:
                # Higher order k-components lie on one side of the cut.
                for part in nx.connected_components(G.subgraph(block - cut)):
                    stack.append((part | cut, max(level, k)))

    return {k: k_components[k] for k in sorted(k_components, reverse=True)}


def _consolidate(sets, k):
    """Merge sets that share k or more elements.

    See: http://rosettacode.org/wiki/Set_consolidation

    The iterative python implementation posted there is
    faster than this because of the overhead of building a
    Graph and calling nx.connected_components, but it's not
    clear for us if we can use it in NetworkX because there
    is no licence for the code.

    """
    G = nx.Graph()
    nodes = dict(enumerate(sets))
    G.add_nodes_from(nodes)
    G.add_edges_from(
        (u, v) for u, v in combinations(nodes, 2) if len(nodes[u] & nodes[v]) >= k
    )
    for component in nx.connected_components(G):
        yield set.union(*[nodes[n] for n in component])


def build_k_number_dict(kcomps):
    return {
        node: k
        for k, comps in sorted(kcomps.items(), key=itemgetter(0))
        for comp in comps
        for node in comp
    }
