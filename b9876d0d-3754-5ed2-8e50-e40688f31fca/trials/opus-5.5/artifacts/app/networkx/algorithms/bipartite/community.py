"""Functions for measuring the quality of a partition of a bipartite graph
into communities."""

import networkx as nx
from networkx.utils import not_implemented_for

__all__ = ["modularity"]


@not_implemented_for("directed")
@nx._dispatchable(edge_attrs="weight", name="bipartite_modularity")
def modularity(G, communities, top_nodes, weight="weight", resolution=1):
    r"""Returns Barber's bipartite modularity of a partition of a bipartite graph.

    The modularity of :func:`networkx.algorithms.community.quality.modularity`
    compares the edges inside communities with a null model in which any two
    nodes may be joined. In a bipartite graph, edges only join the two node
    sets, so Barber [1]_ uses a null model that preserves the degrees and the
    bipartite structure. Calling the two node sets "red" and "blue" nodes,
    the bipartite modularity of a partition is

    .. math::
        Q = \frac{1}{m} \sum_{i \in R} \sum_{j \in B}
            \left( A_{ij} - \gamma \frac{k_i d_j}{m} \right) \delta(c_i, c_j)

    where $R$ and $B$ are the red and blue node sets, $m$ is the number of
    edges (or the sum of all edge weights), $A$ is the adjacency matrix, $k_i$
    and $d_j$ are the (weighted) degrees of the red node $i$ and the blue node
    $j$, $\gamma$ is the resolution parameter and $\delta(c_i, c_j)$ is 1 if
    $i$ and $j$ are in the same community and 0 otherwise. Summing over the
    communities $c$ gives

    .. math::
        Q = \sum_{c} \left( \frac{e_c}{m} - \gamma \frac{R_c B_c}{m^2} \right)

    where $e_c$ is the weight of the edges inside community $c$ and $R_c$
    and $B_c$ are the sums of the degrees of its red and blue nodes.

    Parameters
    ----------
    G : NetworkX graph
        An undirected bipartite graph.

    communities : list or iterable of sets of nodes
        These node sets must represent a partition of G's nodes.

    top_nodes : container of nodes
        The nodes of one of the two node sets of the bipartite graph (the
        "red" nodes). All other nodes of `G` form the other node set. The
        node sets cannot be deduced from `communities` and must be given
        explicitly. See :mod:`bipartite documentation <networkx.algorithms.bipartite>`
        for further details on how bipartite graphs are handled in NetworkX.

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
        The bipartite modularity of the partition.

    Raises
    ------
    NetworkXError
        If `communities` is not a partition of the nodes of `G`, or if an
        edge of `G` does not join a node of `top_nodes` to a node outside
        of `top_nodes`.

    NetworkXNotImplemented
        If `G` is directed.

    Examples
    --------
    >>> from networkx.algorithms import bipartite
    >>> G = nx.Graph([(0, "a"), (0, "b"), (1, "a"), (1, "b"), (1, "c")])
    >>> G.add_edges_from([(2, "c"), (2, "d"), (3, "c"), (3, "d")])
    >>> top_nodes = [0, 1, 2, 3]
    >>> bipartite.modularity(G, [{0, 1, "a", "b"}, {2, 3, "c", "d"}], top_nodes)
    0.3950617283950617

    A single community containing all nodes has modularity $1 - \gamma$:

    >>> bipartite.modularity(G, [set(G)], top_nodes)
    0.0

    See Also
    --------
    networkx.algorithms.community.quality.modularity

    References
    ----------
    .. [1] M. J. Barber, "Modularity and community detection in bipartite
       networks", Phys. Rev. E 76, 066102 (2007).
       https://doi.org/10.1103/PhysRevE.76.066102
    """
    from networkx.algorithms.community.community_utils import is_partition
    from networkx.algorithms.community.quality import NotAPartition

    if not isinstance(communities, list):
        communities = list(communities)
    if not is_partition(G, communities):
        raise NotAPartition(G, communities)

    red = {u for u in G.nbunch_iter(top_nodes)}
    community_of = {u: i for i, comm in enumerate(communities) for u in comm}
    internal = [0] * len(communities)
    m = 0
    for u, v, wt in G.edges(data=weight, default=1):
        if (u in red) == (v in red):
            raise nx.NetworkXError(
                f"Edge ({u!r}, {v!r}) joins two nodes of the same node set: "
                "G is not bipartite with node sets top_nodes and the other nodes"
            )
        m += wt
        if community_of[u] == community_of[v]:
            internal[community_of[u]] += wt

    red_degree = [0] * len(communities)
    blue_degree = [0] * len(communities)
    for u, deg in G.degree(weight=weight):
        if u in red:
            red_degree[community_of[u]] += deg
        else:
            blue_degree[community_of[u]] += deg

    return sum(
        e_c / m - resolution * R_c * B_c / m**2
        for e_c, R_c, B_c in zip(internal, red_degree, blue_degree)
    )


def _red_blue_degrees(G, nodes, weight, red_degree_attr, blue_degree_attr):
    """Returns the total red degree and blue degree of `nodes`.

    The degrees are read from the `red_degree_attr` and `blue_degree_attr`
    node attributes (a missing one counts as 0). For a node with neither
    attribute, its weighted degree is red degree if its ``"bipartite"`` node
    attribute is 0 and blue degree if it is 1. Without that attribute either,
    the node sets are found with :func:`~networkx.algorithms.bipartite.basic.color`.
    """
    red = blue = 0
    coloring = None
    for u in nodes:
        data = G.nodes[u]
        if red_degree_attr in data or blue_degree_attr in data:
            red += data.get(red_degree_attr, 0)
            blue += data.get(blue_degree_attr, 0)
            continue
        side = data.get("bipartite")
        if side not in (0, 1):
            if coloring is None:
                coloring = nx.bipartite.color(G)
            side = coloring[u]
        if side == 0:
            red += G.degree(u, weight=weight)
        else:
            blue += G.degree(u, weight=weight)
    return red, blue


def _bipartite_modularity_merge_delta(
    G,
    community_a,
    community_b,
    resolution,
    weight="weight",
    *,
    red_degree_attr="red_degree",
    blue_degree_attr="blue_degree",
    m,
):
    r"""Returns the change in bipartite modularity from merging two communities.

    Merging two disjoint communities $a$ and $b$ changes the bipartite
    modularity of :func:`modularity` by

    .. math::
        \Delta Q = \frac{e_{ab}}{m} - \gamma \frac{R_a B_b + R_b B_a}{m^2}

    where $e_{ab}$ is the weight of the edges between $a$ and $b$, $R_c$ and
    $B_c$ are the total red and blue degrees of community $c$, $m$ is the
    total edge weight of the graph and $\gamma$ is the resolution.

    The red and blue degrees of each node are read from the node attributes
    `red_degree_attr` and `blue_degree_attr`. This allows nodes that are
    themselves aggregated communities to have both a red and a blue degree.
    For a node without these attributes, its degree is a red degree if its
    ``"bipartite"`` attribute is 0, and a blue degree if it is 1 (or the node
    sets are deduced from a two-coloring of `G` if that attribute is missing).
    Since the bipartite modularity is symmetric in the red and blue node sets,
    which of the two sets is called red does not matter.

    `m` is the total edge weight of the original graph. It is required since
    it cannot be computed from `G` when `G` is an aggregated graph.
    """
    if not isinstance(community_b, set | frozenset):
        community_b = set(community_b)
    multigraph = G.is_multigraph()
    e_ab = 0
    for u in community_a:
        for v, data in G._adj[u].items():
            if v in community_b:
                if multigraph:
                    e_ab += sum(d.get(weight, 1) for d in data.values())
                else:
                    e_ab += data.get(weight, 1)
    attrs = (weight, red_degree_attr, blue_degree_attr)
    R_a, B_a = _red_blue_degrees(G, community_a, *attrs)
    R_b, B_b = _red_blue_degrees(G, community_b, *attrs)
    return e_ab / m - resolution * (R_a * B_b + R_b * B_a) / m**2
