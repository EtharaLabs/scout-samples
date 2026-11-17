"""Functions for measuring the quality of a partition (into
communities).

"""

from collections import Counter
from itertools import combinations

import networkx as nx
from networkx import NetworkXError
from networkx.algorithms.community.community_utils import is_partition
from networkx.utils import not_implemented_for
from networkx.utils.decorators import argmap

__all__ = [
    "modularity",
    "partition_quality",
    "constant_potts_model",
    "overlapping_modularity",
]


class NotAPartition(NetworkXError):
    """Raised if a given collection is not a partition."""

    def __init__(self, G, collection):
        msg = f"{collection} is not a valid partition of the graph {G}"
        super().__init__(msg)


class NotACover(NetworkXError):
    """Raised if a given collection is not a cover of the nodes of a graph."""

    def __init__(self, G, collection):
        msg = f"{collection} is not a valid cover of the nodes of the graph {G}"
        super().__init__(msg)


def _require_partition(G, partition):
    """Decorator to check that a valid partition is input to a function

    Raises :exc:`networkx.NetworkXError` if the partition is not valid.

    This decorator should be used on functions whose first two arguments
    are a graph and a partition of the nodes of that graph (in that
    order)::

        >>> @require_partition
        ... def foo(G, partition):
        ...     print("partition is valid!")
        ...
        >>> G = nx.complete_graph(5)
        >>> partition = [{0, 1}, {2, 3}, {4}]
        >>> foo(G, partition)
        partition is valid!
        >>> partition = [{0}, {2, 3}, {4}]
        >>> foo(G, partition)
        Traceback (most recent call last):
          ...
        networkx.exception.NetworkXError: `partition` is not a valid partition of the nodes of G
        >>> partition = [{0, 1}, {1, 2, 3}, {4}]
        >>> foo(G, partition)
        Traceback (most recent call last):
          ...
        networkx.exception.NetworkXError: `partition` is not a valid partition of the nodes of G

    """
    if is_partition(G, partition):
        return G, partition
    raise nx.NetworkXError("`partition` is not a valid partition of the nodes of G")


require_partition = argmap(_require_partition, (0, 1))


@nx._dispatchable
def intra_community_edges(G, partition):
    """Returns the number of intra-community edges for a partition of `G`.

    Parameters
    ----------
    G : NetworkX graph.

    partition : iterable of sets of nodes
        This must be a partition of the nodes of `G`.

    The "intra-community edges" are those edges joining a pair of nodes
    in the same block of the partition.

    """
    return sum(G.subgraph(block).size() for block in partition)


@nx._dispatchable
def inter_community_edges(G, partition):
    """Returns the number of inter-community edges for a partition of `G`.
    according to the given
    partition of the nodes of `G`.

    Parameters
    ----------
    G : NetworkX graph.

    partition : iterable of sets of nodes
        This must be a partition of the nodes of `G`.

    The *inter-community edges* are those edges joining a pair of nodes
    in different blocks of the partition.

    Implementation note: this function creates an intermediate graph
    that may require the same amount of memory as that of `G`.

    """
    # Alternate implementation that does not require constructing a new
    # graph object (but does require constructing an affiliation
    # dictionary):
    #
    #     aff = dict(chain.from_iterable(((v, block) for v in block)
    #                                    for block in partition))
    #     return sum(1 for u, v in G.edges() if aff[u] != aff[v])
    #
    MG = nx.MultiDiGraph if G.is_directed() else nx.MultiGraph
    return nx.quotient_graph(G, partition, create_using=MG).size()


@nx._dispatchable
def inter_community_non_edges(G, partition):
    """Returns the number of inter-community non-edges according to the
    given partition of the nodes of `G`.

    Parameters
    ----------
    G : NetworkX graph.

    partition : iterable of sets of nodes
        This must be a partition of the nodes of `G`.

    A *non-edge* is a pair of nodes (undirected if `G` is undirected)
    that are not adjacent in `G`. The *inter-community non-edges* are
    those non-edges on a pair of nodes in different blocks of the
    partition.

    Implementation note: this function creates two intermediate graphs,
    which may require up to twice the amount of memory as required to
    store `G`.

    """
    # Alternate implementation that does not require constructing two
    # new graph objects (but does require constructing an affiliation
    # dictionary):
    #
    #     aff = dict(chain.from_iterable(((v, block) for v in block)
    #                                    for block in partition))
    #     return sum(1 for u, v in nx.non_edges(G) if aff[u] != aff[v])
    #
    return inter_community_edges(nx.complement(G), partition)


@nx._dispatchable(edge_attrs="weight")
def modularity(G, communities, weight="weight", resolution=1):
    r"""Returns the modularity of the given partition of the graph.

    Modularity is defined in [1]_ as

    .. math::
        Q = \frac{1}{2m} \sum_{ij} \left( A_{ij} - \gamma\frac{k_ik_j}{2m}\right)
            \delta(c_i,c_j)

    where $m$ is the number of edges (or sum of all edge weights as in [5]_),
    $A$ is the adjacency matrix of `G`, $k_i$ is the (weighted) degree of $i$,
    $\gamma$ is the resolution parameter, and $\delta(c_i, c_j)$ is 1 if $i$ and
    $j$ are in the same community else 0.

    According to [2]_ (and verified by some algebra) this can be reduced to

    .. math::
       Q = \sum_{c=1}^{n}
       \left[ \frac{L_c}{m} - \gamma\left( \frac{k_c}{2m} \right) ^2 \right]

    where the sum iterates over all communities $c$, $m$ is the number of edges,
    $L_c$ is the number of intra-community links for community $c$,
    $k_c$ is the sum of degrees of the nodes in community $c$,
    and $\gamma$ is the resolution parameter.

    The resolution parameter sets an arbitrary tradeoff between intra-group
    edges and inter-group edges. More complex grouping patterns can be
    discovered by analyzing the same network with multiple values of gamma
    and then combining the results [3]_. That said, it is very common to
    simply use gamma=1. More on the choice of gamma is in [4]_.

    The second formula is the one actually used in calculation of the modularity.
    For directed graphs the second formula replaces $k_c$ with $k^{in}_c k^{out}_c$.

    Parameters
    ----------
    G : NetworkX Graph

    communities : list or iterable of set of nodes
        These node sets must represent a partition of G's nodes.

    weight : string or None, optional (default="weight")
        The edge attribute that holds the numerical value used
        as a weight. If None or an edge does not have that attribute,
        then that edge has weight 1.

    resolution : float (default=1)
        If resolution is less than 1, modularity favors larger communities.
        Greater than 1 favors smaller communities.

    Returns
    -------
    Q : float
        The modularity of the partition.

    Raises
    ------
    NotAPartition
        If `communities` is not a partition of the nodes of `G`.

    Examples
    --------
    >>> G = nx.barbell_graph(3, 0)
    >>> nx.community.modularity(G, [{0, 1, 2}, {3, 4, 5}])
    0.35714285714285715
    >>> nx.community.modularity(G, nx.community.label_propagation_communities(G))
    0.35714285714285715

    References
    ----------
    .. [1] M. E. J. Newman "Networks: An Introduction", page 224.
       Oxford University Press, 2011.
    .. [2] Clauset, Aaron, Mark EJ Newman, and Cristopher Moore.
       "Finding community structure in very large networks."
       Phys. Rev. E 70.6 (2004). <https://arxiv.org/abs/cond-mat/0408187>
    .. [3] Reichardt and Bornholdt "Statistical Mechanics of Community Detection"
       Phys. Rev. E 74, 016110, 2006. https://doi.org/10.1103/PhysRevE.74.016110
    .. [4] M. E. J. Newman, "Equivalence between modularity optimization and
       maximum likelihood methods for community detection"
       Phys. Rev. E 94, 052315, 2016. https://doi.org/10.1103/PhysRevE.94.052315
    .. [5] Blondel, V.D. et al. "Fast unfolding of communities in large
       networks" J. Stat. Mech 10008, 1-12 (2008).
       https://doi.org/10.1088/1742-5468/2008/10/P10008
    """
    if not isinstance(communities, list):
        communities = list(communities)
    if not is_partition(G, communities):
        raise NotAPartition(G, communities)

    directed = G.is_directed()
    if directed:
        out_degree = dict(G.out_degree(weight=weight))
        in_degree = dict(G.in_degree(weight=weight))
        m = sum(out_degree.values())
        norm = 1 / m**2
    else:
        out_degree = in_degree = dict(G.degree(weight=weight))
        deg_sum = sum(out_degree.values())
        m = deg_sum / 2
        norm = 1 / deg_sum**2

    def community_contribution(community):
        comm = set(community)
        L_c = sum(wt for u, v, wt in G.edges(comm, data=weight, default=1) if v in comm)

        out_degree_sum = sum(out_degree[u] for u in comm)
        in_degree_sum = sum(in_degree[u] for u in comm) if directed else out_degree_sum

        return L_c / m - resolution * out_degree_sum * in_degree_sum * norm

    return sum(map(community_contribution, communities))


@nx._dispatchable(edge_attrs="weight", node_attrs="node_weight")
def constant_potts_model(
    G, communities, weight="weight", node_weight="node_weight", resolution=1
):
    r"""Returns the constant Potts model (CPM) quality of the partition of `G`.

    The constant Potts model [1]_ compares the weight of the edges inside each
    community with the number of edges the community could hold, scaled by the
    resolution parameter. For an undirected graph it is defined as

    .. math::
        Q = \sum_{c} \left( e_c - \gamma \binom{n_c}{2} \right)

    where the sum iterates over all communities $c$, $e_c$ is the sum of the
    weights of the edges with both endpoints in community $c$, $n_c$ is the
    sum of the node weights of the nodes in community $c$ (the number of nodes
    if no node weights are given) and $\gamma$ is the resolution parameter.
    For directed graphs the number of node pairs $\binom{n_c}{2}$ is replaced
    by the number of ordered node pairs $n_c (n_c - 1)$.

    The resolution parameter acts as a density threshold: communities are
    favoured when their internal edge density exceeds $\gamma$, and
    groups of nodes connected with density below $\gamma$ are better
    split apart [2]_. Unlike :func:`modularity`, this quality function does
    not suffer from the resolution limit, and the singleton partition of a
    graph without self-loops has quality 0.

    Parameters
    ----------
    G : NetworkX Graph

    communities : list or iterable of set of nodes
        These node sets must represent a partition of G's nodes.

    weight : string or None, optional (default="weight")
        The edge attribute that holds the numerical value used
        as a weight. If None or an edge does not have that attribute,
        then that edge has weight 1.

    node_weight : string or None, optional (default="node_weight")
        The node attribute that holds the numerical value used as the
        weight (size) of a node. If None or a node does not have that
        attribute, then that node has weight 1.

    resolution : float (default=1)
        The density threshold $\gamma$. Larger values favor smaller,
        denser communities.

    Returns
    -------
    Q : float
        The constant Potts model quality of the partition.

    Raises
    ------
    NotAPartition
        If `communities` is not a partition of the nodes of `G`.

    Examples
    --------
    >>> G = nx.barbell_graph(3, 0)
    >>> nx.community.constant_potts_model(G, [{0, 1, 2}, {3, 4, 5}])
    0.0
    >>> nx.community.constant_potts_model(G, [{0, 1, 2}, {3, 4, 5}], resolution=0.5)
    3.0
    >>> nx.community.constant_potts_model(G, [set(G)], resolution=0.5)
    -0.5

    See Also
    --------
    modularity
    :any:`leiden_communities`

    References
    ----------
    .. [1] V. A. Traag, P. Van Dooren, and Y. Nesterov,
       "Narrow scope for resolution-limit-free community detection",
       Phys. Rev. E 84, 016114 (2011). https://doi.org/10.1103/PhysRevE.84.016114
    .. [2] V. A. Traag, L. Waltman, and N. J. van Eck, "From Louvain to Leiden:
       guaranteeing well-connected communities", Sci Rep 9, 5233 (2019).
       https://doi.org/10.1038/s41598-019-41695-z
    """
    if not isinstance(communities, list):
        communities = list(communities)
    if not is_partition(G, communities):
        raise NotAPartition(G, communities)

    # number of (ordered, for directed graphs) node pairs in a community of size n
    pair_factor = 1 if G.is_directed() else 0.5
    node_weights = G.nodes(data=node_weight, default=1)

    def community_contribution(community):
        comm = set(community)
        e_c = sum(
            wt for u, v, wt in G.edges(comm, data=weight, default=1) if v in comm
        )
        n_c = sum(node_weights[u] for u in comm)
        return e_c - resolution * pair_factor * n_c * (n_c - 1)

    return sum(map(community_contribution, communities))


def _weight_between(G, nodes, targets, weight, adj):
    """Returns the total weight of the edges in `adj` from `nodes` to `targets`."""
    multigraph = G.is_multigraph()
    total = 0
    for u in nodes:
        for v, data in adj[u].items():
            if v in targets:
                if multigraph:
                    total += sum(d.get(weight, 1) for d in data.values())
                else:
                    total += data.get(weight, 1)
    return total


def _cpm_delta_terms(G, nodes_to_add, community, node_weight):
    """Helper for the CPM quality deltas.

    Returns the nodes that are actually added (those not yet in `community`),
    the community as a set, and the total node weights of both.
    """
    if not isinstance(community, set | frozenset):
        community = set(community)
    new_nodes = {u for u in nodes_to_add if u not in community}
    node_weights = G.nodes(data=node_weight, default=1)
    n_size = sum(node_weights[u] for u in new_nodes)
    comm_size = sum(node_weights[u] for u in community)
    return new_nodes, community, n_size, comm_size


def _quality_delta_cpm_undirected(
    G, nodes_to_add, community, resolution, weight="weight", node_weight="node_weight"
):
    r"""Returns the change in CPM quality from adding nodes to a community.

    The nodes in `nodes_to_add` are assumed to form a community of their own
    before being merged into `community`. For an undirected graph the change
    in :func:`constant_potts_model` quality is

    .. math::
        \Delta Q = E_D - \gamma \, n_{size} \, c_{size}

    where $E_D$ is the total weight of the edges between the added nodes and
    `community`, $n_{size}$ and $c_{size}$ are the total node weights of the
    added nodes and of `community`, and $\gamma$ is the resolution.
    Nodes of `nodes_to_add` that already belong to `community` are ignored.
    """
    new_nodes, community, n_size, comm_size = _cpm_delta_terms(
        G, nodes_to_add, community, node_weight
    )
    E_D = _weight_between(G, new_nodes, community, weight, G._adj)
    return E_D - resolution * n_size * comm_size


def _quality_delta_cpm_directed(
    G, nodes_to_add, community, resolution, weight="weight", node_weight="node_weight"
):
    r"""Returns the change in CPM quality from adding nodes to a community.

    This is the directed counterpart of :func:`_quality_delta_cpm_undirected`.
    Edges in both directions between the added nodes and `community` join
    the community and the number of ordered node pairs grows by
    $2 n_{size} c_{size}$, so that

    .. math::
        \Delta Q = E_D^{out} + E_D^{in} - 2 \gamma \, n_{size} \, c_{size}.

    An undirected graph is treated as the directed graph with both
    orientations of each of its edges.
    """
    new_nodes, community, n_size, comm_size = _cpm_delta_terms(
        G, nodes_to_add, community, node_weight
    )
    succ, pred = (G._succ, G._pred) if G.is_directed() else (G._adj, G._adj)
    E_D_out = _weight_between(G, new_nodes, community, weight, succ)
    E_D_in = _weight_between(G, new_nodes, community, weight, pred)
    return E_D_out + E_D_in - resolution * 2 * n_size * comm_size


@not_implemented_for("directed")
@nx._dispatchable(edge_attrs="weight")
def overlapping_modularity(G, communities, *, weight="weight", resolution=1):
    r"""Returns the extended modularity of a cover of `G` by overlapping communities.

    In a cover, a node may belong to several communities. Shen et al. [1]_
    extend modularity to covers by discounting the contribution of each node
    by the number of communities it belongs to:

    .. math::
        EQ = \frac{1}{2m} \sum_{c} \sum_{i, j \in c} \frac{1}{O_i O_j}
             \left( A_{ij} - \gamma \frac{k_i k_j}{2m} \right)

    where $m$ is the number of edges (or sum of all edge weights), $A$ is the
    adjacency matrix of `G`, $k_i$ is the (weighted) degree of $i$, $O_i$ is
    the number of communities containing node $i$ and $\gamma$ is the
    resolution parameter.

    When every node belongs to exactly one community, the cover is a
    partition and $EQ$ equals :func:`modularity`.

    Parameters
    ----------
    G : NetworkX Graph
        An undirected graph.

    communities : list or iterable of sets of nodes
        These node sets must cover G's nodes: every node of `G` must belong
        to at least one set and the sets may only contain nodes of `G`.
        Unlike for :func:`modularity`, the sets may overlap.

    weight : string or None, optional (default="weight")
        The edge attribute that holds the numerical value used
        as a weight. If None or an edge does not have that attribute,
        then that edge has weight 1.

    resolution : float (default=1)
        If resolution is less than 1, modularity favors larger communities.
        Greater than 1 favors smaller communities.

    Returns
    -------
    EQ : float
        The extended modularity of the cover.

    Raises
    ------
    NetworkXError
        If `communities` is not a cover of the nodes of `G`.

    NetworkXNotImplemented
        If `G` is directed.

    Examples
    --------
    >>> G = nx.barbell_graph(3, 0)
    >>> nx.community.overlapping_modularity(G, [{0, 1, 2}, {3, 4, 5}])
    0.35714285714285715
    >>> cover = [{0, 1, 2, 3}, {2, 3, 4, 5}]
    >>> round(nx.community.overlapping_modularity(G, cover), 6)
    0.142857

    See Also
    --------
    modularity

    References
    ----------
    .. [1] H. Shen, X. Cheng, K. Cai, and M.-B. Hu,
       "Detect overlapping and hierarchical community structure in networks",
       Physica A 388 (8), 1706-1712 (2009).
       https://doi.org/10.1016/j.physa.2008.12.021
    """
    if not isinstance(communities, list):
        communities = list(communities)
    communities = [set(c) for c in communities]
    membership = Counter(u for c in communities for u in c)
    if len(membership) != len(G) or any(u not in G for u in membership):
        raise NotACover(G, communities)

    degree = dict(G.degree(weight=weight))
    deg_sum = sum(degree.values())
    m = deg_sum / 2
    norm = 1 / deg_sum**2

    def community_contribution(comm):
        L_c = sum(
            wt / (membership[u] * membership[v])
            for u, v, wt in G.edges(comm, data=weight, default=1)
            if v in comm
        )
        K_c = sum(degree[u] / membership[u] for u in comm)
        return L_c / m - resolution * K_c * K_c * norm

    return sum(map(community_contribution, communities))


@require_partition
@nx._dispatchable
def partition_quality(G, partition):
    """Returns the coverage and performance of a partition of G.

    The *coverage* of a partition is the ratio of the number of
    intra-community edges to the total number of edges in the graph.

    The *performance* of a partition is the number of
    intra-community edges plus inter-community non-edges divided by the total
    number of potential edges.

    This algorithm has complexity $O(C^2 + L)$ where C is the number of
    communities and L is the number of links.

    Parameters
    ----------
    G : NetworkX graph

    partition : sequence
        Partition of the nodes of `G`, represented as a sequence of
        sets of nodes (blocks). Each block of the partition represents a
        community.

    Returns
    -------
    (float, float)
        The (coverage, performance) tuple of the partition, as defined above.

    Raises
    ------
    NetworkXError
        If `partition` is not a valid partition of the nodes of `G`.

    Notes
    -----
    If `G` is a multigraph;
        - for coverage, the multiplicity of edges is counted
        - for performance, the result is -1 (total number of possible edges is not defined)

    References
    ----------
    .. [1] Santo Fortunato.
           "Community Detection in Graphs".
           *Physical Reports*, Volume 486, Issue 3--5 pp. 75--174
           <https://arxiv.org/abs/0906.0612>
    """

    node_community = {}
    for i, community in enumerate(partition):
        for node in community:
            node_community[node] = i

    # `performance` is not defined for multigraphs
    if not G.is_multigraph():
        # Iterate over the communities, quadratic, to calculate `possible_inter_community_edges`
        possible_inter_community_edges = sum(
            len(p1) * len(p2) for p1, p2 in combinations(partition, 2)
        )

        if G.is_directed():
            possible_inter_community_edges *= 2
    else:
        possible_inter_community_edges = 0

    # Compute the number of edges in the complete graph -- `n` nodes,
    # directed or undirected, depending on `G`
    n = len(G)
    total_pairs = n * (n - 1)
    if not G.is_directed():
        total_pairs //= 2

    intra_community_edges = 0
    inter_community_non_edges = possible_inter_community_edges

    # Iterate over the links to count `intra_community_edges` and `inter_community_non_edges`
    for e in G.edges():
        if node_community[e[0]] == node_community[e[1]]:
            intra_community_edges += 1
        else:
            inter_community_non_edges -= 1

    coverage = intra_community_edges / len(G.edges)

    if G.is_multigraph():
        performance = -1.0
    else:
        performance = (intra_community_edges + inter_community_non_edges) / total_pairs

    return coverage, performance
