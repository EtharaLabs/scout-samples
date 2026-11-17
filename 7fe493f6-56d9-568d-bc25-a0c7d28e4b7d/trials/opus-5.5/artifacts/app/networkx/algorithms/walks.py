"""Functions for counting and generating walks in a graph.

A *walk* is a sequence of nodes in which each adjacent pair of nodes is joined
by an edge of the graph. Each *step* of a walk traverses one edge: parallel
edges of a multigraph are distinct steps, a self-loop is a step that returns to
the same node and, for directed graphs, steps follow the edge direction.
:func:`number_of_walks` counts walks according to this notion of a step and
:func:`random_walk` samples them.
"""

import math
import operator
from bisect import bisect_right
from itertools import accumulate

import networkx as nx
from networkx.utils import py_random_state

__all__ = ["number_of_walks", "random_walk"]


@nx._dispatchable(edge_attrs="weight")
def number_of_walks(G, walk_length, *, weight=None):
    """Returns the number of walks connecting each pair of nodes in `G`

    A *walk* is a sequence of nodes in which each adjacent pair of nodes
    in the sequence is adjacent in the graph. A walk can repeat the same
    edge and go in the opposite direction just as people can walk on a
    set of paths, but standing still is not counted as part of the walk.

    This function only counts the walks with `walk_length` edges. Note that
    the number of nodes in the walk sequence is one more than `walk_length`.
    The number of walks can grow very quickly on a larger graph
    and with a larger walk length.

    Each step of a walk traverses one edge, exactly as a step of
    :func:`random_walk` does: the parallel edges of a multigraph give
    distinct walks, a self-loop gives a step from a node to itself and the
    walks of a directed graph follow the direction of its edges.

    Parameters
    ----------
    G : NetworkX graph

    walk_length : int
        A nonnegative integer representing the length of a walk.

    weight : string or None, optional (default=None)
        If None, every walk counts once. Otherwise this is the edge attribute
        holding the edge weights (missing weights count as 1) and each walk
        contributes the product of the weights of the edges it traverses,
        i.e. the result is given by the powers of the weighted adjacency
        matrix.

    Returns
    -------
    dict
        A dictionary of dictionaries in which outer keys are source
        nodes, inner keys are target nodes, and inner values are the
        number of walks of length `walk_length` connecting those nodes.

    Raises
    ------
    ValueError
        If `walk_length` is negative or not an integer.

    Notes
    -----
    The counts are exact: when they could exceed the range of 64-bit
    integers the computation switches to Python integers.

    Examples
    --------

    >>> G = nx.Graph([(0, 1), (1, 2)])
    >>> walks = nx.number_of_walks(G, 2)
    >>> walks
    {0: {0: 1, 1: 0, 2: 1}, 1: {0: 0, 1: 2, 2: 0}, 2: {0: 1, 1: 0, 2: 1}}
    >>> total_walks = sum(sum(tgts.values()) for _, tgts in walks.items())

    You can also get the number of walks from a specific source node using the
    returned dictionary. For example, number of walks of length 1 from node 0
    can be found as follows:

    >>> walks = nx.number_of_walks(G, 1)
    >>> walks[0]
    {0: 0, 1: 1, 2: 0}
    >>> sum(walks[0].values())  # walks from 0 of length 1
    1

    Similarly, a target node can also be specified:

    >>> walks[0][1]
    1

    Parallel edges are distinct steps:

    >>> nx.number_of_walks(nx.MultiGraph([(0, 1), (0, 1)]), 1)[0][1]
    2

    See Also
    --------
    random_walk
    """
    import scipy as sp

    try:
        walk_length = operator.index(walk_length)
    except TypeError as err:
        raise ValueError(
            f"`walk_length` must be a nonnegative integer: {walk_length!r}"
        ) from err
    if walk_length < 0:
        raise ValueError(f"`walk_length` cannot be negative: {walk_length}")

    if len(G) == 0:
        return {}

    A = nx.adjacency_matrix(G, weight=weight).tocsr()
    if A.dtype.kind in "iub" and _may_overflow(A, walk_length):
        # Fixed width integers would silently overflow: use Python integers.
        power = _exact_matrix_power(A.toarray().astype(object), walk_length)
        return {
            u: {v: power[u_idx, v_idx] for v_idx, v in enumerate(G)}
            for u_idx, u in enumerate(G)
        }
    power = sp.sparse.linalg.matrix_power(A, walk_length).tocsr()
    result = {
        u: {v: power[u_idx, v_idx].item() for v_idx, v in enumerate(G)}
        for u_idx, u in enumerate(G)
    }
    return result


def _may_overflow(A, k):
    """Return True if entries of the integer sparse array ``A ** k`` may not fit
    in a signed 64-bit integer."""
    import scipy as sp

    # cheap bound: entries of A ** k are at most (largest absolute row sum) ** k
    max_row_sum = int(abs(A).sum(axis=1).max())
    if max_row_sum <= 1 or k * math.log2(max_row_sum) <= 62:
        return False
    # otherwise estimate the magnitude of the entries in floating point
    estimate = abs(sp.sparse.linalg.matrix_power(A.astype(float), k)).max()
    return not estimate < 2.0**62


def _exact_matrix_power(A, k):
    """Return ``A ** k`` for a square object array `A` of Python numbers."""
    import numpy as np

    result = np.identity(A.shape[0], dtype=int).astype(object)
    while k:
        if k & 1:
            result = result @ A
        k >>= 1
        if k:
            A = A @ A
    return result


class _StartNodeNotFound(nx.NodeNotFound, nx.NetworkXError):
    """Raised when the start node of a walk is not in the graph.

    It is both a `NodeNotFound` and a `NetworkXError` (the error raised by the
    graph traversals for missing source nodes).
    """


@py_random_state("seed")
@nx._dispatchable(edge_attrs="weight")
def random_walk(G, *, start, weight=None, seed=None):
    """Generate the nodes visited by a random walk on `G` from `start`.

    The walk begins at `start`, which is the first node generated. At every
    step the walk moves from the current node to one of its neighbors
    (successors for directed graphs) by traversing an edge chosen at random,
    and the node reached is generated. Without `weight` every edge leaving
    the current node is equally likely, so parallel edges of a multigraph
    make a neighbor proportionally more likely and a self-loop is a step that
    stays at the same node. With `weight`, each edge is chosen with
    probability proportional to its weight.

    The walk is unbounded: it only stops when it reaches a node from which no
    step is possible (a node without neighbors, or whose edges all have zero
    weight). Use e.g. :func:`itertools.islice` to take a walk of a given
    length; ``k + 1`` generated nodes form a walk of length ``k``, the same
    notion of length used by :func:`number_of_walks`.

    Parameters
    ----------
    G : NetworkX graph

    start : node
        The node where the walk starts. This argument is keyword-only.

    weight : string or None, optional (default=None)
        The edge attribute used to bias the choice of each step. Each edge is
        traversed with probability proportional to this attribute (missing
        values count as 1; weights must be nonnegative). If None, all edges
        are equally likely.

    seed : integer, random_state, or None (default)
        Indicator of random number generation state.
        See :ref:`Randomness<randomness>`.

    Returns
    -------
    generator
        A generator of the nodes visited by the walk, starting with `start`.

    Raises
    ------
    NodeNotFound
        If `start` is not a node of `G` (the exception is also a
        `NetworkXError`).

    ValueError
        If `weight` is given and the walk meets an edge with a negative weight.

    Notes
    -----
    The transition probabilities are those of the row-normalized (weighted)
    adjacency matrix, so the probability of each walk of length `k` from
    `start` is given by products of entries of that matrix. The graph should
    not be modified while the walk is being generated.

    Examples
    --------
    >>> from itertools import islice
    >>> G = nx.cycle_graph(5)
    >>> walk = list(islice(nx.random_walk(G, start=0, seed=42), 6))
    >>> len(walk), walk[0]
    (6, 0)
    >>> all(G.has_edge(u, v) for u, v in nx.utils.pairwise(walk))
    True

    The walk ends where no further step is possible:

    >>> list(nx.random_walk(nx.DiGraph([(0, 1), (1, 2)]), start=0))
    [0, 1, 2]

    Edge weights bias the walk; an edge of weight zero is never traversed:

    >>> G = nx.Graph([(0, 1, {"w": 1}), (0, 2, {"w": 0}), (1, 2, {"w": 1})])
    >>> walk = list(islice(nx.random_walk(G, start=0, weight="w", seed=1), 20))
    >>> any({u, v} == {0, 2} for u, v in nx.utils.pairwise(walk))
    False

    See Also
    --------
    number_of_walks
    generate_random_paths
    """
    if start not in G:
        raise _StartNodeNotFound(f"Starting node {start} is not in G")
    return _random_walk(G, start, weight, seed)


def _random_walk(G, node, weight, seed):
    """Generator behind :func:`random_walk`; `node` is the start node."""
    succ = G._succ if G.is_directed() else G._adj
    multigraph = G.is_multigraph()
    steps = {}
    while True:
        yield node
        try:
            nbrs, cumulative = steps[node]
        except KeyError:
            nbrs, cumulative = steps[node] = _step_choices(
                succ[node], weight, multigraph
            )
        if not nbrs:
            return
        if cumulative is None:
            node = seed.choice(nbrs)
        else:
            # as in random.choices, `hi` guards against floating point round-off
            x = seed.random() * cumulative[-1]
            node = nbrs[bisect_right(cumulative, x, 0, len(cumulative) - 1)]


def _step_choices(nbrdict, weight, multigraph):
    """Return the possible next nodes of a walk and their cumulative weights.

    Without `weight` the returned list holds each neighbor once per edge (so a
    uniform choice from it picks a uniformly random edge) and the cumulative
    weights are None. With `weight`, the cumulative edge weights towards each
    neighbor are returned. An empty neighbor list means no step is possible.
    """
    if weight is None:
        if multigraph:
            return [nbr for nbr, keydict in nbrdict.items() for _ in keydict], None
        return list(nbrdict), None
    nbrs = []
    weights = []
    for nbr, data in nbrdict.items():
        edges = data.values() if multigraph else (data,)
        for dd in edges:
            wt = dd.get(weight, 1)
            if wt < 0:
                raise ValueError(f"Negative edge weight {wt!r} found on a random walk")
            if wt:
                nbrs.append(nbr)
                weights.append(wt)
    if not nbrs:
        return [], None
    return nbrs, list(accumulate(weights))
