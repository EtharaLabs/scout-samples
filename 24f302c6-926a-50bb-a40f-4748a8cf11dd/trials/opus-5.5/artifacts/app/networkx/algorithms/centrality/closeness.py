"""
Closeness centrality measures.
"""

import functools

import networkx as nx
from networkx.exception import NetworkXError
from networkx.utils.decorators import not_implemented_for

__all__ = ["closeness_centrality", "incremental_closeness_centrality"]


@nx._dispatchable(edge_attrs="distance")
def closeness_centrality(G, u=None, distance=None, wf_improved=True):
    r"""Compute closeness centrality for nodes.

    Closeness centrality [1]_ of a node `u` is the reciprocal of the
    average shortest path distance to `u` over all `n-1` reachable nodes.

    .. math::

        C(u) = \frac{n - 1}{\sum_{v=1}^{n-1} d(v, u)},

    where `d(v, u)` is the shortest-path distance between `v` and `u`,
    and `n-1` is the number of nodes reachable from `u`. Notice that the
    closeness distance function computes the incoming distance to `u`
    for directed graphs. To use outward distance, act on `G.reverse()`.

    Notice that higher values of closeness indicate higher centrality.

    Wasserman and Faust propose an improved formula for graphs with
    more than one connected component. The result is "a ratio of the
    fraction of actors in the group who are reachable, to the average
    distance" from the reachable actors [2]_. You might think this
    scale factor is inverted but it is not. As is, nodes from small
    components receive a smaller closeness value. Letting `N` denote
    the number of nodes in the graph,

    .. math::

        C_{WF}(u) = \frac{n-1}{N-1} \frac{n - 1}{\sum_{v=1}^{n-1} d(v, u)},

    Parameters
    ----------
    G : graph
      A NetworkX graph

    u : node, optional
      Return only the value for node u

    distance : edge attribute key, optional (default=None)
      Use the specified edge attribute as the edge distance in shortest
      path calculations.  If `None` (the default) all edges have a distance of 1.
      Absent edge attributes are assigned a distance of 1. Note that no check
      is performed to ensure that edges have the provided attribute.

    wf_improved : bool, optional (default=True)
      If True, scale by the fraction of nodes reachable. This gives the
      Wasserman and Faust improved formula. For single component graphs
      it is the same as the original formula.

    Returns
    -------
    nodes : dictionary
      Dictionary of nodes with closeness centrality as the value.

    Examples
    --------
    >>> G = nx.Graph([(0, 1), (0, 2), (0, 3), (1, 2), (1, 3)])
    >>> nx.closeness_centrality(G)
    {0: 1.0, 1: 1.0, 2: 0.75, 3: 0.75}

    See Also
    --------
    betweenness_centrality, load_centrality, eigenvector_centrality,
    degree_centrality, incremental_closeness_centrality

    Notes
    -----
    The closeness centrality is normalized to `(n-1)/(|G|-1)` where
    `n` is the number of nodes in the connected part of graph
    containing the node.  If the graph is not completely connected,
    this algorithm computes the closeness centrality for each
    connected part separately scaled by that parts size.

    If the 'distance' keyword is set to an edge attribute key then the
    shortest-path length will be computed using Dijkstra's algorithm with
    that edge attribute as the edge weight.

    The closeness centrality uses *inward* distance to a node, not outward.
    If you want to use outword distances apply the function to `G.reverse()`

    In NetworkX 2.2 and earlier a bug caused Dijkstra's algorithm to use the
    outward distance rather than the inward distance. If you use a 'distance'
    keyword and a DiGraph, your results will change between v2.2 and v2.3.

    References
    ----------
    .. [1] Linton C. Freeman: Centrality in networks: I.
       Conceptual clarification. Social Networks 1:215-239, 1979.
       https://doi.org/10.1016/0378-8733(78)90021-7
    .. [2] pg. 201 of Wasserman, S. and Faust, K.,
       Social Network Analysis: Methods and Applications, 1994,
       Cambridge University Press.
    """
    if G.is_directed():
        G = G.reverse()  # create a reversed graph view

    if distance is not None:
        # use Dijkstra's algorithm with specified attribute as edge weight
        path_length = functools.partial(
            nx.single_source_dijkstra_path_length, weight=distance
        )
    else:
        path_length = nx.single_source_shortest_path_length

    if u is None:
        nodes = G.nodes
    else:
        nodes = [u]
    len_G = len(G)
    closeness_dict = {
        n: _closeness_from_lengths(path_length(G, n), len_G, wf_improved)
        for n in nodes
    }
    if u is not None:
        return closeness_dict[u]
    return closeness_dict


def _closeness_from_lengths(lengths, n_nodes, wf_improved):
    """Returns the closeness centrality of a node from its distances.

    Parameters
    ----------
    lengths : dict
        Maps every node at finite distance from the node (the node itself
        included, at distance 0) to that distance.

    n_nodes : int
        Number of nodes in the whole graph.

    wf_improved : bool
        If True, scale by the fraction of the other nodes of the graph that
        are at finite distance (Wasserman and Faust).

    Notes
    -----
    The plain reciprocal of the distance sum is only meaningful when every
    other node is at finite distance. The average is therefore taken over
    the `r` other nodes at finite distance only, giving ``r / sum(lengths)``,
    and a node at finite distance from no other node (or a graph with a
    single node) has closeness 0. A distance sum of 0, which only happens
    with zero edge distances, is also given closeness 0.
    """
    # Number of other nodes at finite distance.
    reachable = len(lengths) - 1
    total = sum(lengths.values())
    if reachable <= 0 or n_nodes <= 1 or total <= 0:
        return 0.0
    closeness = reachable / total
    if wf_improved:
        # normalize to number of nodes-1 in connected part
        closeness *= reachable / (n_nodes - 1)
    return closeness


@not_implemented_for("directed")
@nx._dispatchable(mutates_input=True)
def incremental_closeness_centrality(
    G, edge, prev_cc=None, insertion=True, wf_improved=True
):
    r"""Incremental closeness centrality for nodes.

    Compute closeness centrality for nodes using level-based work filtering
    as described in Incremental Algorithms for Closeness Centrality by Sariyuce et al.

    Level-based work filtering detects unnecessary updates to the closeness
    centrality and filters them out.

    ---
    From "Incremental Algorithms for Closeness Centrality":

    Theorem 1: Let :math:`G = (V, E)` be a graph and u and v be two vertices in V
    such that there is no edge (u, v) in E. Let :math:`G' = (V, E \cup uv)`
    Then :math:`cc[s] = cc'[s]` if and only if :math:`\left|dG(s, u) - dG(s, v)\right| \leq 1`.

    Where :math:`dG(u, v)` denotes the length of the shortest path between
    two vertices u, v in a graph G, cc[s] is the closeness centrality for a
    vertex s in V, and cc'[s] is the closeness centrality for a
    vertex s in V, with the (u, v) edge added.
    ---

    We use Theorem 1 to filter out updates when adding or removing an edge.
    When adding an edge (u, v), we compute the shortest path lengths from all
    other nodes to u and to v before the node is added. When removing an edge,
    we compute the shortest path lengths after the edge is removed. Then we
    apply Theorem 1 to use previously computed closeness centrality for nodes
    where :math:`\left|dG(s, u) - dG(s, v)\right| \leq 1`. This works only for
    undirected, unweighted graphs; the distance argument is not supported.

    Closeness centrality [1]_ of a node `u` is the reciprocal of the
    sum of the shortest path distances from `u` to all `n-1` other nodes.
    Since the sum of distances depends on the number of nodes in the
    graph, closeness is normalized by the sum of minimum possible
    distances `n-1`.

    .. math::

        C(u) = \frac{n - 1}{\sum_{v=1}^{n-1} d(v, u)},

    where `d(v, u)` is the shortest-path distance between `v` and `u`,
    and `n` is the number of nodes in the graph.

    Notice that higher values of closeness indicate higher centrality.

    Parameters
    ----------
    G : graph
      A NetworkX graph

    edge : tuple
      The modified edge (u, v) in the graph.

    prev_cc : dictionary
      The previous closeness centrality for all nodes in the graph, that is,
      the closeness centrality of `G` computed with the same `wf_improved`.
      If None, the closeness centrality of the modified graph is computed
      from scratch.

    insertion : bool, optional
      If True (default) the edge was inserted, otherwise it was deleted from the graph.

    wf_improved : bool, optional (default=True)
      If True, scale by the fraction of nodes reachable. This gives the
      Wasserman and Faust improved formula. For single component graphs
      it is the same as the original formula.

    Returns
    -------
    nodes : dictionary
      Dictionary of nodes with closeness centrality as the value, for the
      graph obtained by inserting (or deleting) `edge` in `G`. `G` itself
      is left unchanged.

    Raises
    ------
    NetworkXError
      If `prev_cc` and `G` do not have the same nodes, or if `insertion` is
      False and `edge` is not in `G`.

    See Also
    --------
    betweenness_centrality, load_centrality, eigenvector_centrality,
    degree_centrality, closeness_centrality

    Notes
    -----
    The closeness centrality is normalized to `(n-1)/(|G|-1)` where
    `n` is the number of nodes in the connected part of graph
    containing the node.  If the graph is not completely connected,
    this algorithm computes the closeness centrality for each
    connected part separately.

    References
    ----------
    .. [1] Freeman, L.C., 1979. Centrality in networks: I.
       Conceptual clarification.  Social Networks 1, 215--239.
       https://doi.org/10.1016/0378-8733(78)90021-7
    .. [2] Sariyuce, A.E. ; Kaya, K. ; Saule, E. ; Catalyiirek, U.V. Incremental
       Algorithms for Closeness Centrality. 2013 IEEE International Conference on Big Data
       http://sariyuce.com/papers/bigdata13.pdf
    """
    if prev_cc is not None and set(prev_cc.keys()) != set(G.nodes()):
        raise NetworkXError("prev_cc and G do not have the same nodes")

    # Unpack edge
    (u, v) = edge
    path_length = nx.single_source_shortest_path_length

    if insertion and G.has_edge(u, v):
        # Inserting an edge that is already there does not change the graph.
        if prev_cc is None:
            return nx.closeness_centrality(G, wf_improved=wf_improved)
        return dict(prev_cc)

    if insertion:
        # For edge insertion, we want shortest paths before the edge is inserted
        du = path_length(G, u)
        dv = path_length(G, v)

        G.add_edge(u, v)
    else:
        if not G.has_edge(u, v):
            raise NetworkXError(f"The edge {u}-{v} is not in the graph")
        # Keep the removed edge, with its data, to restore it as it was.
        if G.is_multigraph():
            # Like remove_edge(u, v), remove the most recently added edge.
            key = list(G[u][v])[-1]
            removed_edge = (u, v, key, G[u][v][key])
            G.remove_edge(u, v, key)
        else:
            removed_edge = (u, v, G[u][v])
            G.remove_edge(u, v)

        # For edge removal, we want shortest paths after the edge is removed
        du = path_length(G, u)
        dv = path_length(G, v)

    try:
        if prev_cc is None:
            return nx.closeness_centrality(G, wf_improved=wf_improved)

        len_G = len(G)
        closeness_dict = {}
        for n in G:
            if n in du and n in dv:
                if abs(du[n] - dv[n]) <= 1:
                    # Theorem 1: the distances from n are unchanged.
                    closeness_dict[n] = prev_cc[n]
                    continue
            elif n not in du and n not in dv:
                # n is in a connected component containing neither u nor v,
                # which the change of the edge does not affect.
                closeness_dict[n] = prev_cc[n]
                continue
            closeness_dict[n] = _closeness_from_lengths(
                path_length(G, n), len_G, wf_improved
            )
        return closeness_dict
    finally:
        # Leave the graph as we found it
        if insertion:
            G.remove_edge(u, v)
        else:
            G.add_edges_from([removed_edge])
