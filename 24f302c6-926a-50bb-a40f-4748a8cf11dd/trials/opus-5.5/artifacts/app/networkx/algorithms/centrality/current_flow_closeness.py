"""Current-flow closeness centrality measures."""

import networkx as nx
from networkx.algorithms.centrality.flow_matrix import (
    CGInverseLaplacian,
    FullInverseLaplacian,
    SuperLUInverseLaplacian,
)
from networkx.utils import not_implemented_for, reverse_cuthill_mckee_ordering

__all__ = ["current_flow_closeness_centrality", "information_centrality"]


@not_implemented_for("directed")
@nx._dispatchable(edge_attrs="weight")
def current_flow_closeness_centrality(G, weight=None, dtype=float, solver="lu"):
    r"""Compute current-flow closeness centrality for nodes.

    Current-flow closeness centrality is variant of closeness
    centrality based on effective resistance between nodes in
    a network. This metric is also known as information centrality.

    The current-flow closeness centrality of a node $v$ is

    .. math::

        c(v) = \frac{1}{\sum_{w \neq v} R(v, w)},

    where $R(v, w)$ is the effective resistance between $v$ and $w$ when
    every edge is a resistor of conductance equal to its weight. Effective
    resistances are derived from the Laplacian matrix $L$ of the graph:
    $R(v, w) = C_{vv} + C_{ww} - 2 C_{vw}$ for a generalized inverse $C$ of
    $L$. Unlike closeness centrality, all paths between two nodes
    contribute, not only the shortest ones.

    Parameters
    ----------
    G : graph
      A NetworkX graph.

    weight : None or string, optional (default=None)
      If None, all edge weights are considered equal.
      Otherwise holds the name of the edge attribute used as weight.
      The weight reflects the capacity or the strength of the
      edge.

    dtype: data type (default=float)
      Default data type for internal matrices.
      Set to np.float32 for lower memory consumption.

    solver: string (default='lu')
       Type of linear solver to use for computing the flow matrix.
       Options are "full" (uses most memory), "lu" (recommended), and
       "cg" (uses least memory).

    Returns
    -------
    nodes : dictionary
       Dictionary of nodes with current flow closeness centrality as the value.
       The only node of a graph with a single node has centrality 0.

    Raises
    ------
    NetworkXError
        If the graph is not connected.

    NetworkXPointlessConcept
        If the graph has no nodes.

    See Also
    --------
    closeness_centrality

    Notes
    -----
    The algorithm is from Brandes [1]_.

    See also [2]_ for the original definition of information centrality.

    References
    ----------
    .. [1] Ulrik Brandes and Daniel Fleischer,
       Centrality Measures Based on Current Flow.
       Proc. 22nd Symp. Theoretical Aspects of Computer Science (STACS '05).
       LNCS 3404, pp. 533-544. Springer-Verlag, 2005.
       https://doi.org/10.1007/978-3-540-31856-9_44

    .. [2] Karen Stephenson and Marvin Zelen:
       Rethinking centrality: Methods and examples.
       Social Networks 11(1):1-37, 1989.
       https://doi.org/10.1016/0378-8733(89)90016-6
    """
    import numpy as np

    if not nx.is_connected(G):
        raise nx.NetworkXError("Graph not connected.")
    if len(G) == 1:
        # There is no other node to be close to.
        return dict.fromkeys(G, 0.0)
    solvername = {
        "full": FullInverseLaplacian,
        "lu": SuperLUInverseLaplacian,
        "cg": CGInverseLaplacian,
    }
    N = G.number_of_nodes()
    # Order the rows and columns of the Laplacian with the reverse
    # Cuthill-McKee ordering to reduce its bandwidth: index i is node ordering[i]
    ordering = list(reverse_cuthill_mckee_ordering(G))
    L = nx.laplacian_matrix(G, nodelist=ordering, weight=weight).asformat("csc")
    L = L.astype(dtype)
    # The solver yields the rows of the generalized inverse C of L obtained by
    # grounding node 0: the inverse of L without row and column 0, padded
    # with zeros. Then R(v, w) = C[v, v] + C[w, w] - 2 C[v, w], hence
    # sum_w R(v, w) = N C[v, v] + trace(C) - 2 sum_w C[v, w].
    C2 = solvername[solver](L, width=1, dtype=dtype)  # initialize solver
    diagonal = np.zeros(N)
    row_sums = np.zeros(N)
    for v in range(N):
        row = C2.get_row(v)
        diagonal[v] = row[v]
        row_sums[v] = row.sum(dtype=float)
    resistance_sums = N * diagonal + diagonal.sum() - 2 * row_sums
    return {ordering[v]: float(1 / r) for v, r in enumerate(resistance_sums)}


information_centrality = current_flow_closeness_centrality
