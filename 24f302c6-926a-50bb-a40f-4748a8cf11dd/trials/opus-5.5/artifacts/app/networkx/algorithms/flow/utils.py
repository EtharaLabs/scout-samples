"""
Utility classes and functions for network flow algorithms.
"""

from collections import deque

import networkx as nx

__all__ = [
    "CurrentEdge",
    "Level",
    "GlobalRelabelThreshold",
    "build_residual_network",
    "detect_unboundedness",
    "build_flow_dict",
]


class CurrentEdge:
    """Mechanism for iterating over out-edges incident to a node in a circular
    manner. StopIteration exception is raised when wraparound occurs.
    """

    __slots__ = ("_edges", "_it", "_curr")

    def __init__(self, edges):
        self._edges = edges
        if self._edges:
            self._rewind()

    def get(self):
        return self._curr

    def move_to_next(self):
        try:
            self._curr = next(self._it)
        except StopIteration:
            self._rewind()
            raise

    def _rewind(self):
        self._it = iter(self._edges.items())
        self._curr = next(self._it)

    def __eq__(self, other):
        return (getattr(self, "_curr", None), self._edges) == (
            (getattr(other, "_curr", None), other._edges)
        )


class Level:
    """Active and inactive nodes in a level."""

    __slots__ = ("active", "inactive")

    def __init__(self):
        self.active = set()
        self.inactive = set()


class GlobalRelabelThreshold:
    """Measurement of work before the global relabeling heuristic should be
    applied.
    """

    def __init__(self, n, m, freq):
        self._threshold = (n + m) / freq if freq else float("inf")
        self._work = 0

    def add_work(self, work):
        self._work += work

    def is_reached(self):
        return self._work >= self._threshold

    def clear_work(self):
        self._work = 0


def _capacity_function(G, capacity):
    """Returns a function that returns the capacity of an edge.

    This is the single place where the flow algorithms resolve edge
    capacities, so that all of them agree on how a capacity is read and on
    what a missing capacity means.

    Parameters
    ----------
    G : NetworkX graph
        The graph whose edges are queried. MultiGraph and MultiDiGraph are
        not supported.

    capacity : string or function
        If it is callable, `capacity` itself is returned. It must accept
        exactly three positional arguments: the two endpoints of an edge
        and the edge attribute dictionary for that edge, and it must return
        either a number, the capacity of the edge, or None to indicate that
        the edge is hidden, that is, it is ignored by the flow algorithms.

        If it is a string, it is the name of the edge attribute that holds
        the capacity of an edge. In that case a function is returned that
        reads that attribute; edges without the attribute are considered to
        have infinite capacity.

    Returns
    -------
    function
        A function with signature ``(u, v, d)`` returning the capacity of
        the edge ``(u, v)`` with attribute dictionary ``d``, or None if the
        edge is to be ignored.

    Raises
    ------
    NetworkXError
        If `G` is a MultiGraph or a MultiDiGraph.

    Examples
    --------
    >>> from networkx.algorithms.flow.utils import _capacity_function
    >>> G = nx.DiGraph()
    >>> G.add_edge("x", "y", capacity=3)
    >>> G.add_edge("y", "z")
    >>> cap = _capacity_function(G, "capacity")
    >>> cap("x", "y", G["x"]["y"])
    3
    >>> cap("y", "z", G["y"]["z"])
    inf
    >>> def hide_yz(u, v, d):
    ...     return None if (u, v) == ("y", "z") else d.get("capacity", 1)
    >>> _capacity_function(G, hide_yz) is hide_yz
    True
    """
    if G.is_multigraph():
        raise nx.NetworkXError("MultiGraph and MultiDiGraph not supported (yet).")
    if callable(capacity):
        return capacity
    # The capacity is the name of an edge attribute. Missing attributes mean
    # that the edge can carry an unlimited amount of flow.
    inf = float("inf")
    return lambda u, v, d: d.get(capacity, inf)


@nx._dispatchable(
    edge_attrs={"capacity": float("inf")},
    preserve_edge_attrs="capacity",
    returns_graph=True,
)
def build_residual_network(G, capacity):
    """Build a residual network and initialize a zero flow.

    The residual network :samp:`R` from an input graph :samp:`G` has the
    same nodes as :samp:`G`. :samp:`R` is a DiGraph that contains a pair
    of edges :samp:`(u, v)` and :samp:`(v, u)` iff :samp:`(u, v)` is not a
    self-loop, and at least one of :samp:`(u, v)` and :samp:`(v, u)` exists
    in :samp:`G` with a positive capacity.

    For each edge :samp:`(u, v)` in :samp:`R`, :samp:`R[u][v]['capacity']`
    is equal to the capacity of :samp:`(u, v)` in :samp:`G` if it exists
    in :samp:`G` or zero otherwise. If the capacity is infinite,
    :samp:`R[u][v]['capacity']` will have a high arbitrary finite value
    that does not affect the solution of the problem. This value is stored in
    :samp:`R.graph['inf']`. For each edge :samp:`(u, v)` in :samp:`R`,
    :samp:`R[u][v]['flow']` represents the flow function of :samp:`(u, v)` and
    satisfies :samp:`R[u][v]['flow'] == -R[v][u]['flow']`.

    The flow value, defined as the total flow into :samp:`t`, the sink, is
    stored in :samp:`R.graph['flow_value']`. If :samp:`cutoff` is not
    specified, reachability to :samp:`t` using only edges :samp:`(u, v)` such
    that :samp:`R[u][v]['flow'] < R[u][v]['capacity']` induces a minimum
    :samp:`s`-:samp:`t` cut.

    Parameters
    ----------
    G : NetworkX graph
        The input graph. MultiGraph and MultiDiGraph are not supported.

    capacity : string or function
        If it is a string, it is the name of the edge attribute holding the
        capacity of an edge; edges without that attribute are considered to
        have infinite capacity. If it is a function, it is called as
        ``capacity(u, v, d)`` for each edge ``(u, v)`` with attribute
        dictionary ``d`` and must return the capacity of the edge, or None
        to leave the edge out of the residual network.

    Returns
    -------
    R : NetworkX DiGraph
        The residual network, with a zero flow.

    Raises
    ------
    NetworkXError
        If `G` is a MultiGraph or a MultiDiGraph.
    """
    capacity = _capacity_function(G, capacity)

    R = nx.DiGraph()
    R.__networkx_cache__ = None  # Disable caching
    R.add_nodes_from(G)

    inf = float("inf")
    # Extract edges with positive capacities. Self loops and edges hidden by
    # the capacity function are excluded. The capacity of each edge is
    # resolved exactly once.
    edge_list = []
    for u, v, attr in G.edges(data=True):
        if u == v:
            continue
        cap = capacity(u, v, attr)
        if cap is not None and cap > 0:
            edge_list.append((u, v, cap))
    # Simulate infinity with three times the sum of the finite edge capacities
    # or any positive value if the sum is zero. This allows the
    # infinite-capacity edges to be distinguished for unboundedness detection
    # and directly participate in residual capacity calculation. If the maximum
    # flow is finite, these edges cannot appear in the minimum cut and thus
    # guarantee correctness. Since the residual capacity of an
    # infinite-capacity edge is always at least 2/3 of inf, while that of an
    # finite-capacity edge is at most 1/3 of inf, if an operation moves more
    # than 1/3 of inf units of flow to t, there must be an infinite-capacity
    # s-t path in G.
    inf = 3 * sum(cap for u, v, cap in edge_list if cap != inf) or 1
    if G.is_directed():
        for u, v, cap in edge_list:
            r = min(cap, inf)
            if not R.has_edge(u, v):
                # Both (u, v) and (v, u) must be present in the residual
                # network.
                R.add_edge(u, v, capacity=r)
                R.add_edge(v, u, capacity=0)
            else:
                # The edge (u, v) was added when (v, u) was visited.
                R[u][v]["capacity"] = r
    else:
        for u, v, cap in edge_list:
            # Add a pair of edges with equal residual capacities.
            r = min(cap, inf)
            R.add_edge(u, v, capacity=r)
            R.add_edge(v, u, capacity=r)

    # Record the value simulating infinity.
    R.graph["inf"] = inf

    return R


@nx._dispatchable(
    graphs="R",
    preserve_edge_attrs={"R": {"capacity": float("inf")}},
    preserve_graph_attrs=True,
)
def detect_unboundedness(R, s, t):
    """Detect an infinite-capacity s-t path in R."""
    q = deque([s])
    seen = {s}
    inf = R.graph["inf"]
    while q:
        u = q.popleft()
        for v, attr in R[u].items():
            if attr["capacity"] == inf and v not in seen:
                if v == t:
                    raise nx.NetworkXUnbounded(
                        "Infinite capacity path, flow unbounded above."
                    )
                seen.add(v)
                q.append(v)


@nx._dispatchable(graphs={"G": 0, "R": 1}, preserve_edge_attrs={"R": {"flow": None}})
def build_flow_dict(G, R):
    """Build a flow dictionary from a residual network."""
    flow_dict = {}
    for u in G:
        flow_dict[u] = {v: 0 for v in G[u]}
        flow_dict[u].update(
            (v, attr["flow"]) for v, attr in R[u].items() if attr["flow"] > 0
        )
    return flow_dict
