"""Functions for detecting communities based on Leiden Community Detection
algorithm.
"""

import math
from collections import defaultdict, deque

import networkx as nx
from networkx.algorithms.community.louvain import (
    _gen_graph,
    _neighbor_weights,
    _prepare_graph,
)
from networkx.utils import not_implemented_for, py_random_state

__all__ = ["leiden_communities", "leiden_partitions"]

_METRICS = ("cpm", "modularity")


@not_implemented_for("directed")
@py_random_state("seed")
@nx._dispatchable(edge_attrs="weight")
def leiden_communities(
    G,
    *,
    weight="weight",
    resolution=1.0,
    max_level=None,
    seed=None,
    metric="cpm",
    theta=0.01,
):
    r"""Find a best partition of `G` using Leiden Community Detection.

    Leiden Community Detection [1]_ is an algorithm to extract the community
    structure of a network by optimizing a quality function, either the
    Constant Potts Model (see :any:`constant_potts_model`) or modularity
    (see :any:`modularity`). It is an improvement upon the Louvain Community
    Detection algorithm (see :any:`louvain_communities`): unlike the Louvain
    algorithm, it guarantees that communities are well connected, in addition
    to being faster and uncovering better partitions.

    The algorithm works in 3 phases. On the first phase, it adds the nodes to a
    queue in random order. For each node it tries to find the maximum positive
    gain in the quality function by moving the node to one of its neighbor
    communities or to a new, empty community. If a node is moved from its
    community, it adds to the rear of the queue all neighbors of the node that
    do not belong to the node's new community and that are not in the queue.

    The first phase continues until the queue is empty.

    The second phase consists in refining the partition $P$ obtained from the
    first phase. It starts with a singleton partition $P_{refined}$. Then it
    merges nodes locally in $P_{refined}$ within each community of the
    partition $P$. Nodes are merged with a community in $P_{refined}$ only if
    both are sufficiently well connected to their community in $P$. Among the
    communities a node may join without decreasing the quality, one is chosen
    at random with probability proportional to $\exp(\Delta H / \theta)$,
    where $\Delta H$ is the change in quality (measured in units of edge
    weight) and $\theta$ is the randomness parameter. This means that after the
    refinement phase is concluded, communities in $P$ sometimes will have been
    split into multiple communities.

    The third phase consists of aggregating the network by building a new
    network whose nodes are now the communities found in the second phase.
    However, the non-refined partition is used to create an initial partition
    for the aggregate network.

    Once this phase is complete it is possible to reapply the first and second
    phases creating bigger communities with increased quality.

    The above three phases are executed until the quality function stops
    improving or `max_level` levels have been computed. Communities that are
    disconnected after the first phase are split into their connected
    components, which does not decrease the quality for a nonnegative
    resolution, so that all communities of the returned partition are
    connected.

    The quality function is selected with the `metric` parameter:

    ``"cpm"``
        The Constant Potts Model. With a resolution $\gamma$ it rewards
        communities whose internal edge density exceeds $\gamma$, so
        useful values of `resolution` for unweighted graphs are between 0
        and 1. A node $v$ joining community $C$ changes the quality by
        $E(v, C) - \gamma n_v n_C$, where $E(v, C)$ is the weight of the
        edges between $v$ and $C$ and $n$ counts nodes.
    ``"modularity"``
        The modularity of the partition, in which case `resolution` plays
        the same role as in :any:`louvain_communities`.

    Be careful with self-loops in the input graph. These are treated as
    previously reduced communities -- as if the process had been started
    in the middle of the algorithm.

    Parameters
    ----------
    G : NetworkX graph
        An undirected graph.
    weight : string or None, optional (default="weight")
        The name of an edge attribute that holds the numerical value
        used as a weight. If None then each edge has weight 1.
    resolution : float, optional (default=1.0)
        The resolution parameter $\gamma$ of the quality function. Larger
        values favor smaller communities.
    max_level : int or None, optional (default=None)
        The maximum number of levels (steps of the algorithm) to compute.
        Must be a positive integer or None. If None, then there is no max
        level and the algorithm will run until converged.
    seed : integer, random_state, or None (default)
        Indicator of random number generation state.
        See :ref:`Randomness<randomness>`.
    metric : {"cpm", "modularity"}, optional (default="cpm")
        The quality function to optimize: the Constant Potts Model or
        modularity.
    theta : float, optional (default=0.01)
        The randomness of the refinement phase. Must be nonnegative. Smaller
        values make the refinement more greedy; with ``theta=0`` the
        community with the largest gain is always chosen.

    Returns
    -------
    list
        A list of disjoint sets (partition of `G`). Each set represents one
        community. All communities together contain all the nodes in `G`.

    Raises
    ------
    NetworkXNotImplemented
        If `G` is directed.
    ValueError
        If `max_level` is not a positive integer or None, if `metric` is not
        a supported quality function or if `theta` is negative.

    Examples
    --------
    >>> G = nx.barbell_graph(5, 0)
    >>> nx.community.leiden_communities(G, metric="modularity", seed=42)
    [{0, 1, 2, 3, 4}, {5, 6, 7, 8, 9}]

    With the Constant Potts Model, the resolution acts as a density threshold:
    the larger it is, the denser and smaller the communities found.

    >>> G = nx.karate_club_graph()
    >>> [
    ...     len(nx.community.leiden_communities(G, weight=None, resolution=r, seed=42))
    ...     for r in (0.05, 0.1, 0.5)
    ... ]
    [2, 5, 20]

    For an unweighted graph and the default resolution of 1, no group of nodes
    is denser than the threshold, so every node is its own community.

    Notes
    -----
    The order in which the nodes are considered can affect the final output.
    In the algorithm the ordering happens using a random shuffle.

    References
    ----------
    .. [1] Traag, V.A., Waltman, L. & van Eck, N.J. From Louvain to Leiden: guaranteeing
       well-connected communities. Sci Rep 9, 5233 (2019). https://doi.org/10.1038/s41598-019-41695-z

    See Also
    --------
    leiden_partitions
    :any:`louvain_communities`
    :any:`constant_potts_model`
    :any:`modularity`
    """
    partitions = leiden_partitions(
        G,
        weight=weight,
        resolution=resolution,
        max_level=max_level,
        seed=seed,
        metric=metric,
        theta=theta,
    )
    final_partition = deque(partitions, maxlen=1)
    return final_partition.pop()


@not_implemented_for("directed")
@py_random_state("seed")
@nx._dispatchable(edge_attrs="weight")
def leiden_partitions(
    G,
    *,
    weight="weight",
    resolution=1.0,
    max_level=None,
    seed=None,
    metric="cpm",
    theta=0.01,
):
    """Yield partitions for each level of Leiden Community Detection

    Leiden Community Detection is an algorithm to extract the community
    structure of a network by optimizing a quality function, either the
    Constant Potts Model or modularity.

    The partitions across levels (steps of the algorithm) form a dendrogram
    of communities. A dendrogram is a diagram representing a tree and each
    level represents a partition of the G graph. The top level contains the
    smallest communities and as you traverse to the bottom of the tree the
    communities get bigger and the overall quality increases making
    the partition better.

    Each level is generated by executing the three phases of the Leiden Community
    Detection algorithm. See :any:`leiden_communities`.

    Parameters
    ----------
    G : NetworkX graph
        An undirected graph.
    weight : string or None, optional (default="weight")
        The name of an edge attribute that holds the numerical value
        used as a weight. If None then each edge has weight 1.
    resolution : float, optional (default=1.0)
        The resolution parameter of the quality function. Larger values
        favor smaller communities.
    max_level : int or None, optional (default=None)
        The maximum number of levels (partitions) to compute.
        Must be a positive integer or None. If None, then there is no max
        level and the algorithm will run until converged.
    seed : integer, random_state, or None (default)
        Indicator of random number generation state.
        See :ref:`Randomness<randomness>`.
    metric : {"cpm", "modularity"}, optional (default="cpm")
        The quality function to optimize: the Constant Potts Model or
        modularity.
    theta : float, optional (default=0.01)
        The randomness of the refinement phase. Must be nonnegative.

    Yields
    ------
    list
        A list of disjoint sets (partition of `G`). Each set represents one community.
        All communities together contain all the nodes in `G`. The yielded partitions
        strictly increase the quality function with each iteration.

    Raises
    ------
    NetworkXNotImplemented
        If `G` is directed.
    ValueError
        If `max_level` is not a positive integer or None, if `metric` is not
        a supported quality function or if `theta` is negative.

    Examples
    --------
    >>> G = nx.path_graph(8)
    >>> for partition in nx.community.leiden_partitions(G, metric="modularity", seed=1):
    ...     print(partition)
    [{0, 1}, {2, 3}, {4, 5}, {6, 7}]
    [{0, 1, 2, 3}, {4, 5, 6, 7}]

    References
    ----------
    .. [1] Traag, V.A., Waltman, L. & van Eck, N.J. From Louvain to Leiden: guaranteeing
       well-connected communities. Sci Rep 9, 5233 (2019). https://doi.org/10.1038/s41598-019-41695-z

    See Also
    --------
    leiden_communities
    :any:`louvain_partitions`
    """
    # Validate the arguments now rather than when the first partition is requested.
    if max_level is not None and max_level <= 0:
        raise ValueError("max_level argument must be a positive integer or None")
    if not isinstance(metric, str) or metric.lower() not in _METRICS:
        raise ValueError(f"metric must be one of {_METRICS}, not {metric!r}")
    if theta < 0:
        raise ValueError(f"theta must be nonnegative, not {theta}")
    return _leiden_levels(G, weight, resolution, max_level, seed, metric.lower(), theta)


def _leiden_levels(G, weight, resolution, max_level, seed, metric, theta):
    """Generator yielding the partitions of `G` found at each Leiden level.

    Within this generator, quality differences are measured in units of edge
    weight: moving node `v` into community `C` changes the quality by
    ``E(v, C) - gamma * size(v) * size(C)``. For the Constant Potts Model the
    size of a node is its node weight (number of original nodes) and
    ``gamma = resolution``. For modularity the size of a node is its weighted
    degree and ``gamma = resolution / (2 * m)``, which gives the change in
    modularity multiplied by `m`.
    """
    partition = [{u} for u in G]
    graph = _prepare_graph(G, weight)
    m = graph.size(weight="weight")
    if graph.number_of_edges() == 0 or (metric == "modularity" and m == 0):
        yield partition
        return
    gamma = resolution if metric == "cpm" else resolution / (2 * m)
    node_index = {u: i for i, u in enumerate(G)}

    # The communities of the current (aggregated) graph, as lists of its nodes.
    communities = [[u] for u in graph]
    level = 0
    while True:
        nbrs = {
            u: {v: d["weight"] for v, d in nbrdict.items() if v != u}
            for u, nbrdict in graph.adjacency()
        }
        if metric == "cpm":
            sizes = dict(graph.nodes(data="node_weight", default=1))
        else:
            sizes = dict(graph.degree(weight="weight"))

        communities, moved = _move_nodes_fast(nbrs, sizes, communities, gamma, seed)
        if level > 0 and not moved:
            # The quality did not improve: the last yielded partition is final.
            return
        communities = _split_disconnected(nbrs, sizes, communities, gamma)
        level += 1
        yield _flatten(graph, communities, node_index)

        if level == max_level or len(communities) == len(graph):
            # Either the level cap is reached, or every community is a single
            # node of the aggregated graph and nothing is left to aggregate.
            return
        refined = _refine_partition(nbrs, sizes, communities, gamma, theta, seed)
        node_weight = "node_weight" if metric == "cpm" else None
        graph = _gen_graph(graph, refined, node_weight=node_weight)
        # The initial partition of the aggregated graph is the non-refined one.
        block = {u: i for i, part in enumerate(refined) for u in part}
        communities = [
            list(dict.fromkeys(block[u] for u in comm)) for comm in communities
        ]


def _flatten(graph, communities, node_index):
    """Returns the partition of the original nodes represented by `communities`.

    The communities are sorted by their first node in the original node order.
    """
    partition = []
    for comm in communities:
        nodes = set()
        for u in comm:
            nodes.update(graph.nodes[u].get("nodes", {u}))
        partition.append(nodes)
    partition.sort(key=lambda nodes: min(node_index[u] for u in nodes))
    return partition


def _move_nodes_fast(nbrs, sizes, communities, gamma, seed):
    """First phase of the Leiden algorithm: queue based local moving of nodes.

    Each node in the queue moves to the neighboring (or empty) community that
    increases the quality the most, if any. When a node moves, its neighbors
    outside of its new community are queued again.

    Returns the new communities (as lists of nodes, ordered by first node in
    the iteration order of `nbrs`) and whether any node moved.
    """
    node2com = {}
    com_size = {}
    com_count = {}
    for label, comm in enumerate(communities):
        for u in comm:
            node2com[u] = label
        com_size[label] = sum(sizes[u] for u in comm)
        com_count[label] = len(comm)
    next_label = len(communities)
    # magnitudes used to tell real quality gains from floating point noise
    total_size = sum(abs(s) for s in sizes.values())
    strength = {u: sum(abs(w) for w in nbrdict.values()) for u, nbrdict in nbrs.items()}

    queue = list(nbrs)
    seed.shuffle(queue)
    queue = deque(queue)
    in_queue = set(queue)
    moved = False
    # Every accepted move strictly increases the quality, so the loop ends.
    # As a safeguard against pathological floating point behavior, the number
    # of node visits is bounded as well.
    max_visits = 100 * len(nbrs) + 10_000
    visits = 0
    while queue and visits < max_visits:
        visits += 1
        u = queue.popleft()
        in_queue.discard(u)
        cur = node2com[u]
        size = sizes[u]
        weights2com = _neighbor_weights(nbrs[u], node2com)
        com_size[cur] -= size
        com_count[cur] -= 1
        # quality contribution of u to its current community (without u)
        stay = weights2com.get(cur, 0.0) - gamma * size * com_size[cur]
        best_com = cur
        best_gain = 0.0
        for com, wt in weights2com.items():
            if com != cur:
                gain = wt - gamma * size * com_size[com] - stay
                if gain > best_gain:
                    best_gain = gain
                    best_com = com
        if com_count[cur] > 0 and -stay > best_gain:
            # isolating u in a new community is the best option
            best_gain = -stay
            best_com = None
        # Only accept moves whose gain exceeds the floating point noise so that
        # round-off cannot make nodes move back and forth forever.
        scale = strength[u] + abs(gamma * size) * total_size
        if best_com != cur and best_gain <= 1e-12 * scale:
            best_com = cur
        if best_com is None:
            best_com = next_label
            next_label += 1
            com_size[best_com] = 0
            com_count[best_com] = 0
        com_size[best_com] += size
        com_count[best_com] += 1
        if best_com != cur:
            node2com[u] = best_com
            moved = True
            for v in nbrs[u]:
                if node2com[v] != best_com and v not in in_queue:
                    queue.append(v)
                    in_queue.add(v)

    new_communities = defaultdict(list)
    for u in nbrs:
        new_communities[node2com[u]].append(u)
    return list(new_communities.values()), moved


def _split_disconnected(nbrs, sizes, communities, gamma):
    """Split communities that are not connected into their connected components.

    No edge joins two components, so splitting a community into components
    with sizes ``s_1, ..., s_k`` changes the quality by
    ``gamma * sum(s_i * s_j for i < j)``. This is nonnegative for nonnegative
    resolutions and sizes, and then the split guarantees that all communities
    are connected. Communities are only split if this does not decrease the
    quality.
    """
    result = []
    for comm in communities:
        if len(comm) == 1:
            result.append(comm)
            continue
        members = set(comm)
        component_of = {}
        components = []
        for start in comm:
            if start in component_of:
                continue
            idx = len(components)
            component_of[start] = idx
            stack = [start]
            while stack:
                u = stack.pop()
                for v in nbrs[u]:
                    if v in members and v not in component_of:
                        component_of[v] = idx
                        stack.append(v)
            components.append([])
        if len(components) == 1:
            result.append(comm)
            continue
        for u in comm:
            components[component_of[u]].append(u)
        component_sizes = [sum(sizes[u] for u in c) for c in components]
        total = sum(component_sizes)
        pair_sum = (total * total - sum(s * s for s in component_sizes)) / 2
        if gamma * pair_sum >= 0:
            result.extend(components)
        else:
            result.append(comm)
    return result


def _refine_partition(nbrs, sizes, communities, gamma, theta, seed):
    """Second phase of the Leiden algorithm: refine each community.

    Within every community, starting from singletons, each well connected
    node that is still alone may merge with a well connected sub-community.
    The sub-community is chosen at random among those that do not decrease
    the quality, with probability proportional to ``exp(gain / theta)``.
    Returns the refined partition as a list of lists of nodes.
    """
    refined = []
    for comm in communities:
        if len(comm) == 1:
            refined.append(list(comm))
            continue
        members = set(comm)
        comm_size = sum(sizes[u] for u in comm)
        # weight of the edges between each node and the rest of the community
        ext = {u: sum(w for v, w in nbrs[u].items() if v in members) for u in comm}
        label = {u: u for u in comm}
        sub_size = {u: sizes[u] for u in comm}
        sub_ext = dict(ext)
        sub_count = dict.fromkeys(comm, 1)

        order = list(comm)
        seed.shuffle(order)
        for u in order:
            cur = label[u]
            size = sizes[u]
            if sub_count[cur] != 1:
                continue  # u is no longer alone in its sub-community
            if ext[u] < gamma * size * (comm_size - size):
                continue  # u is not well connected to its community
            weights2sub = defaultdict(float)
            for v, w in nbrs[u].items():
                if v in members:
                    weights2sub[label[v]] += w
            candidates = [cur]
            gains = [0.0]
            for sub, wt in weights2sub.items():
                if sub == cur:
                    continue
                s = sub_size[sub]
                if sub_ext[sub] < gamma * s * (comm_size - s):
                    continue  # sub-community not well connected to its community
                gain = wt - gamma * size * s
                if gain >= 0:
                    candidates.append(sub)
                    gains.append(gain)
            if len(candidates) == 1:
                continue
            chosen = _random_candidate(candidates, gains, theta, seed)
            if chosen != cur:
                label[u] = chosen
                sub_count[cur] -= 1
                sub_count[chosen] += 1
                sub_size[chosen] += size
                sub_ext[chosen] += ext[u] - 2 * weights2sub[chosen]

        subs = defaultdict(list)
        for u in comm:
            subs[label[u]].append(u)
        refined.extend(subs.values())
    return refined


def _random_candidate(candidates, gains, theta, seed):
    """Choose a candidate with probability proportional to ``exp(gain / theta)``.

    With ``theta == 0`` a candidate with the largest gain is chosen uniformly.
    """
    max_gain = max(gains)
    if theta == 0:
        best = [c for c, g in zip(candidates, gains) if g == max_gain]
        return best[0] if len(best) == 1 else seed.choice(best)
    weights = [math.exp((g - max_gain) / theta) for g in gains]
    r = seed.random() * sum(weights)
    for candidate, w in zip(candidates, weights):
        r -= w
        if r < 0:
            return candidate
    return candidates[-1]
