"""Functions for splitting a network into two communities (finding a bipartition)."""

from itertools import count

import networkx as nx
from networkx.algorithms.community.community_utils import is_partition
from networkx.utils import BinaryHeap, not_implemented_for, py_random_state

__all__ = [
    "kernighan_lin_bisection",
    "spectral_modularity_bipartition",
    "greedy_node_swap_bipartition",
]


class _InvalidSplit(nx.NetworkXError, ValueError):
    """Raised when an initial split is not a partition of the nodes into two sets."""


def _kernighan_lin_sweep(edges, side):
    """
    This is a modified form of Kernighan-Lin, which moves single nodes at a
    time, alternating between sides to keep the bisection balanced.  We keep
    two min-heaps of swap costs to make optimal-next-move selection fast.
    """
    costs0, costs1 = costs = BinaryHeap(), BinaryHeap()
    for u, side_u, edges_u in zip(count(), side, edges):
        cost_u = sum(w if side[v] else -w for v, w in edges_u)
        costs[side_u].insert(u, cost_u if side_u else -cost_u)

    def _update_costs(costs_x, x):
        for y, w in edges[x]:
            costs_y = costs[side[y]]
            cost_y = costs_y.get(y)
            if cost_y is not None:
                cost_y += 2 * (-w if costs_x is costs_y else w)
                costs_y.insert(y, cost_y, True)

    i = 0
    totcost = 0
    while costs0 and costs1:
        u, cost_u = costs0.pop()
        _update_costs(costs0, u)
        v, cost_v = costs1.pop()
        _update_costs(costs1, v)
        totcost += cost_u + cost_v
        i += 1
        yield totcost, i, (u, v)


@not_implemented_for("directed")
@py_random_state(4)
@nx._dispatchable(edge_attrs="weight")
def kernighan_lin_bisection(G, partition=None, max_iter=10, weight="weight", seed=None):
    """Partition a graph into two blocks using the Kernighan–Lin
    algorithm.

    This algorithm partitions a network into two sets by iteratively
    swapping pairs of nodes to reduce the edge cut between the two sets.  The
    pairs are chosen according to a modified form of Kernighan-Lin [1]_, which
    moves node individually, alternating between sides to keep the bisection
    balanced.

    Parameters
    ----------
    G : NetworkX graph
        Graph must be undirected.

    partition : tuple
        Pair of iterables containing an initial partition. If not
        specified, a random balanced partition is used.

    max_iter : int
        Maximum number of times to attempt swaps to find an
        improvement before giving up.

    weight : key
        Edge data key to use as weight. If None, the weights are all
        set to one.

    seed : integer, random_state, or None (default)
        Indicator of random number generation state.
        See :ref:`Randomness<randomness>`.
        Only used if partition is None

    Returns
    -------
    partition : tuple
        A pair of sets of nodes representing the bipartition.

    Raises
    ------
    NetworkXError
        If partition is not a valid partition of the nodes of the graph.

    See Also
    --------
    spectral_modularity_bipartition
    greedy_node_swap_bipartition

    References
    ----------
    .. [1] Kernighan, B. W.; Lin, Shen (1970).
       "An efficient heuristic procedure for partitioning graphs."
       *Bell Systems Technical Journal* 49: 291--307.
       Oxford University Press 2011.

    """
    n = len(G)
    labels = list(G)
    seed.shuffle(labels)
    index = {v: i for i, v in enumerate(labels)}

    if partition is None:
        side = [0] * (n // 2) + [1] * ((n + 1) // 2)
    else:
        try:
            A, B = partition
        except (TypeError, ValueError) as err:
            raise nx.NetworkXError("partition must be two sets") from err
        if not is_partition(G, (A, B)):
            raise nx.NetworkXError("partition invalid")
        side = [0] * n
        for a in A:
            side[index[a]] = 1

    if G.is_multigraph():
        edges = [
            [
                (index[u], sum(e.get(weight, 1) for e in d.values()))
                for u, d in G[v].items()
            ]
            for v in labels
        ]
    else:
        edges = [
            [(index[u], e.get(weight, 1)) for u, e in G[v].items()] for v in labels
        ]

    for i in range(max_iter):
        costs = list(_kernighan_lin_sweep(edges, side))
        min_cost, min_i, _ = min(costs)
        if min_cost >= 0:
            break

        for _, _, (u, v) in costs[:min_i]:
            side[u] = 1
            side[v] = 0

    A = {u for u, s in zip(labels, side) if s == 0}
    B = {u for u, s in zip(labels, side) if s == 1}
    return A, B


@not_implemented_for("directed")
@nx._dispatchable
def spectral_modularity_bipartition(G):
    r"""Returns a bipartition of the nodes based on the spectrum of the
    modularity matrix of `G`.

    This method [1]_ computes the leading eigenvector of the modularity matrix,
    i.e. the eigenvector associated with its largest eigenvalue. The
    modularity matrix $B$ is defined by

    .. math::
        B_{ij} = A_{ij} - \frac{k_i k_j}{2m},

    where $A$ is the adjacency matrix, $k_i$ is the degree of node $i$ and
    $m$ is the number of edges in the graph (see
    :func:`~networkx.linalg.modularitymatrix.modularity_matrix`).
    Nodes whose components in the eigenvector are negative are placed in one
    block, the other nodes are placed in the other block.

    Edge weights are ignored. The result is deterministic: the sign of the
    eigenvector, which is arbitrary, is chosen such that the first block
    contains the first node of `G` whose component is nonzero. Components
    that vanish up to round-off errors are treated as zero.

    Parameters
    ----------
    G : NetworkX graph
        An undirected graph.

    Returns
    -------
    C : tuple of sets
        Pair of communities as two sets of nodes of `G`, partitioned according
        to the signs of the leading eigenvector of the modularity matrix.

    Raises
    ------
    NetworkXNotImplemented
        If `G` is directed.

    Examples
    --------
    >>> G = nx.karate_club_graph()
    >>> MrHi, Officer = nx.community.spectral_modularity_bipartition(G)
    >>> sorted(MrHi)
    [0, 1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 16, 17, 19, 21]
    >>> sorted(Officer)
    [8, 9, 14, 15, 18, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33]

    Notes
    -----
    If `G` has no edges the modularity matrix is not defined, and all the nodes
    are put in the second block.

    See Also
    --------
    greedy_node_swap_bipartition
    kernighan_lin_bisection
    :func:`~networkx.linalg.modularitymatrix.modularity_matrix`

    References
    ----------
    .. [1] M. E. J. Newman, "Modularity and community structure in networks",
       PNAS, 103 (23), p. 8577-8582, 2006.
       https://doi.org/10.1073/pnas.0601602103
    .. [2] M. E. J. Newman, *Networks: An Introduction*, pages 373--378,
       Oxford University Press, 2010.
    """
    import numpy as np

    if G.number_of_edges() == 0:
        return set(), set(G)
    A = nx.to_numpy_array(G, weight=None)
    k = A.sum(axis=1)
    B = A - np.outer(k, k) / k.sum()
    _, eigenvectors = np.linalg.eigh(B)  # eigenvalues in ascending order
    leading = eigenvectors[:, -1]
    nonzero = np.flatnonzero(np.abs(leading) > 1e-12)
    if leading[nonzero[0]] > 0:
        leading = -leading
    negative = {u for u, x in zip(G, leading) if x < -1e-12}
    return negative, set(G) - negative


@not_implemented_for("directed")
@nx._dispatchable(preserve_edge_attrs={"G": {"weight": 1}})
def greedy_node_swap_bipartition(G, *, init_split=None, max_iter=10):
    """Split the nodes of `G` into two communities by greedy modularity maximization.

    Starting from an initial split, the algorithm [1]_ repeatedly moves the
    single node whose move to the other community increases the
    :func:`~networkx.algorithms.community.quality.modularity` the most (or
    decreases it the least). Each node is moved at most once during an
    iteration, and the best split seen during the iteration is kept. The next
    iteration starts from that split. The algorithm stops when an iteration
    does not improve the modularity or after `max_iter` iterations.

    Modularity is computed with the ``"weight"`` edge attribute (an edge
    without it has weight 1) and a resolution of 1, as with the default
    arguments of :func:`~networkx.algorithms.community.quality.modularity`.

    Parameters
    ----------
    G : NetworkX graph
        An undirected graph.

    init_split : pair of sets of nodes, optional (default=None)
        A pair of sets of nodes of `G` that form a partition of its nodes,
        used as initial split. If None, the first half of the nodes of `G`
        (in the order of ``G.nodes``) forms the first set and the other nodes
        form the second set.

    max_iter : int, optional (default=10)
        Maximum number of iterations, each attempting to improve the split
        by moving every node once.

    Returns
    -------
    split : tuple of sets
        A pair of sets of nodes of `G` forming a partition of its nodes. The
        modularity of `split` is at least that of `init_split`.

    Raises
    ------
    NetworkXError
        If `init_split` is not a partition of the nodes of `G` into two sets.
        The raised error is also a :exc:`ValueError`.

    NetworkXNotImplemented
        If `G` is directed.

    Examples
    --------
    >>> G = nx.barbell_graph(3, 0)
    >>> nx.community.greedy_node_swap_bipartition(G, init_split=({0, 1, 3}, {2, 4, 5}))
    ({0, 1, 2}, {3, 4, 5})

    Notes
    -----
    Each iteration takes $O(n^2 + m)$ time for a graph with $n$ nodes and $m$
    edges. If `G` has no edges, modularity is not defined and the initial
    split is returned.

    See Also
    --------
    spectral_modularity_bipartition
    kernighan_lin_bisection

    References
    ----------
    .. [1] M. E. J. Newman, *Networks: An Introduction*, pages 373--375,
       Oxford University Press, 2010.
    """
    nodes = list(G)
    if init_split is None:
        half = len(nodes) // 2
        side = dict.fromkeys(nodes[:half], 0) | dict.fromkeys(nodes[half:], 1)
    else:
        try:
            first, second = init_split
            first, second = set(first), set(second)
        except (TypeError, ValueError) as err:
            raise _InvalidSplit("init_split must be a pair of sets of nodes") from err
        if not is_partition(G, [first, second]):
            raise _InvalidSplit("init_split must be a partition of the nodes of G")
        side = dict.fromkeys(first, 0) | dict.fromkeys(second, 1)

    # weights of the edges between distinct nodes, parallel edges summed
    multigraph = G.is_multigraph()
    nbrs = {}
    for u, nbrdict in G.adjacency():
        nbrs[u] = {
            v: (
                sum(d.get("weight", 1) for d in data.values())
                if multigraph
                else data.get("weight", 1)
            )
            for v, data in nbrdict.items()
            if v != u
        }
    degree = dict(G.degree(weight="weight"))
    two_m = sum(degree.values())
    if two_m == 0:
        return {u for u in nodes if side[u] == 0}, {u for u in nodes if side[u] == 1}

    # weights from each node to each side, and total degree of each side
    w_to = {u: [0, 0] for u in nodes}
    for u in nodes:
        for v, w in nbrs[u].items():
            w_to[u][side[v]] += w
    side_degree = [0, 0]
    for u in nodes:
        side_degree[side[u]] += degree[u]

    def move(u):
        s = side[u]
        t = 1 - s
        side[u] = t
        side_degree[s] -= degree[u]
        side_degree[t] += degree[u]
        for v, w in nbrs[u].items():
            w_to[v][s] -= w
            w_to[v][t] += w

    for _ in range(max_iter):
        # Modularity changes are tracked in units of 1 / m:
        # moving u from side s to side t changes m * Q by
        #   w(u, t) - w(u, s) - k_u (K_t - K_s + k_u) / 2m
        unmoved = dict.fromkeys(nodes)
        moves = []
        gain = best_gain = 0
        best_num_moves = 0
        while unmoved:
            best_node = None
            for u in unmoved:
                s = side[u]
                t = 1 - s
                du = w_to[u][t] - w_to[u][s]
                du -= degree[u] * (side_degree[t] - side_degree[s] + degree[u]) / two_m
                if best_node is None or du > best_du:
                    best_node, best_du = u, du
            move(best_node)
            del unmoved[best_node]
            moves.append(best_node)
            gain += best_du
            if gain > best_gain:
                best_gain = gain
                best_num_moves = len(moves)
        # undo the moves made after the best split of this iteration
        for u in reversed(moves[best_num_moves:]):
            move(u)
        if best_num_moves == 0:
            break

    return {u for u in nodes if side[u] == 0}, {u for u in nodes if side[u] == 1}
