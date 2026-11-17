"""
====================
Biadjacency matrices
====================
"""

import itertools

import networkx as nx
from networkx.convert_matrix import _generate_weighted_edges

__all__ = ["biadjacency_matrix", "from_biadjacency_matrix"]


class _InvalidNodeOrder(nx.NetworkXError, ValueError):
    """Raised when a node ordering does not match the shape of a matrix."""


@nx._dispatchable(edge_attrs="weight")
def biadjacency_matrix(
    G, row_order, column_order=None, dtype=None, weight="weight", format="csr"
):
    r"""Returns the biadjacency matrix of the bipartite graph G.

    Let `G = (U, V, E)` be a bipartite graph with node sets
    `U = u_{1},...,u_{r}` and `V = v_{1},...,v_{s}`. The biadjacency
    matrix [1]_ is the `r` x `s` matrix `B` in which `b_{i,j} = 1`
    if, and only if, `(u_i, v_j) \in E`. If the parameter `weight` is
    not `None` and matches the name of an edge attribute, its value is
    used instead of 1.

    Parameters
    ----------
    G : graph
       A NetworkX graph

    row_order : list of nodes
       The rows of the matrix are ordered according to the list of nodes.

    column_order : list, optional
       The columns of the matrix are ordered according to the list of nodes.
       If column_order is None, then the columns are the nodes of `G` that
       are not in `row_order`, in the order of ``G.nodes``.

    dtype : NumPy data-type, optional
        A valid NumPy dtype used to initialize the array. If None, then the
        NumPy default is used.

    weight : string or None, optional (default='weight')
       The edge data key used to provide each value in the matrix.
       If None, then each edge has weight 1.

    format : str in {'dense', 'bsr', 'csr', 'csc', 'coo', 'lil', 'dia', 'dok'}
        The type of the matrix to be returned (default 'csr'). For
        some algorithms different implementations of sparse matrices
        can perform better.  See [2]_ for details. With 'dense', a
        NumPy array is returned.

    Returns
    -------
    M : SciPy sparse array
        Biadjacency matrix representation of the bipartite graph G.

    Raises
    ------
    NetworkXError
        If `row_order` is empty, if `row_order` or `column_order` contain
        duplicates or nodes that are not in `G`, or if `format` is not valid.

    Examples
    --------
    >>> from networkx.algorithms import bipartite
    >>> G = nx.Graph([("a", 1), ("a", 2), ("b", 2)])
    >>> M = bipartite.biadjacency_matrix(G, ["a", "b"], [1, 2])
    >>> M.toarray()
    array([[1, 1],
           [0, 1]])

    The graph can be recovered, with the same node labels, using
    :func:`from_biadjacency_matrix`:

    >>> H = bipartite.from_biadjacency_matrix(
    ...     M, row_order=["a", "b"], column_order=[1, 2]
    ... )
    >>> sorted(H.edges, key=str)
    [('a', 1), ('a', 2), ('b', 2)]

    Notes
    -----
    No attempt is made to check that the input graph is bipartite.

    For directed bipartite graphs only successors are considered as neighbors.
    To obtain an adjacency matrix with ones (or weight values) for both
    predecessors and successors you have to generate two biadjacency matrices
    where the rows of one of them are the columns of the other, and then add
    one to the transpose of the other.

    For multigraphs the matrix values are the sums of the weights of the
    parallel edges.

    See Also
    --------
    adjacency_matrix
    from_biadjacency_matrix

    References
    ----------
    .. [1] https://en.wikipedia.org/wiki/Adjacency_matrix#Adjacency_matrix_of_a_bipartite_graph
    .. [2] Scipy Dev. References, "Sparse Matrices",
       https://docs.scipy.org/doc/scipy/reference/sparse.html
    """
    import scipy as sp

    row_order = list(row_order)
    nlen = len(row_order)
    if nlen == 0:
        raise nx.NetworkXError("row_order is empty list")
    row_index = _node_index(G, row_order, "row_order")
    if column_order is None:
        column_order = [n for n in G if n not in row_index]
    else:
        column_order = list(column_order)
    mlen = len(column_order)
    col_index = _node_index(G, column_order, "column_order")

    multigraph = G.is_multigraph()
    row, col, data = [], [], []
    for u in row_order:
        i = row_index[u]
        for v, edgedata in G._adj[u].items():
            j = col_index.get(v)
            if j is None:
                continue
            row.append(i)
            col.append(j)
            if multigraph:
                data.append(sum(d.get(weight, 1) for d in edgedata.values()))
            else:
                data.append(edgedata.get(weight, 1))
    A = sp.sparse.coo_array((data, (row, col)), shape=(nlen, mlen), dtype=dtype)
    try:
        return A.asformat(format)
    except ValueError as err:
        raise nx.NetworkXError(f"Unknown sparse array format: {format}") from err


def _node_index(G, nodes, name):
    """Returns a dict mapping each node of the list `nodes` to its position.

    Raises NetworkXError if `nodes` contains duplicates or nodes not in `G`.
    """
    index = dict(zip(nodes, itertools.count()))
    if len(index) != len(nodes):
        msg = f"Ambiguous ordering: `{name}` contained duplicates."
        raise nx.NetworkXError(msg)
    for n in nodes:
        if n not in G:
            raise nx.NetworkXError(f"Node {n} in {name} is not in G")
    return index


@nx._dispatchable(graphs=None, returns_graph=True)
def from_biadjacency_matrix(
    A, create_using=None, edge_attribute="weight", row_order=None, column_order=None
):
    r"""Creates a new bipartite graph from a biadjacency matrix given as a
    SciPy sparse array.

    Parameters
    ----------
    A: scipy sparse array
      A biadjacency matrix representation of a graph. Dense arrays (for
      example NumPy arrays) are also accepted.

    create_using: NetworkX graph
       Use specified graph for result.  The default is Graph()

    edge_attribute: string
       Name of edge attribute to store matrix numeric value. The data will
       have the same type as the matrix entry (int, float, (real,imag)).

    row_order : list, optional (default: ``range(n)``)
        The nodes represented by the rows of the `n` x `m` matrix `A`, in
        order. They are added to the graph with the ``bipartite`` node
        attribute set to 0. Must have one node per row of `A`.

    column_order : list, optional (default: ``range(n, n + m)``)
        The nodes represented by the columns of `A`, in order. They are
        added to the graph with the ``bipartite`` node attribute set to 1.
        Must have one node per column of `A`.

    Returns
    -------
    G : NetworkX graph
        A bipartite graph with an edge from the node of row `i` to the node
        of column `j` for each nonzero entry ``A[i, j]``.

    Raises
    ------
    NetworkXError
        If `row_order` or `column_order` does not contain one node per row
        or column of `A`, contains duplicates, or if the two share nodes.
        This error is also a :exc:`ValueError`.

    Examples
    --------
    >>> import scipy as sp
    >>> from networkx.algorithms import bipartite
    >>> A = sp.sparse.csr_array([[1, 0, 2], [0, 3, 0]])
    >>> G = bipartite.from_biadjacency_matrix(A)
    >>> sorted(G.edges(data="weight"))
    [(0, 2, 1), (0, 4, 2), (1, 3, 3)]

    The rows and columns can be mapped to other nodes:

    >>> G = bipartite.from_biadjacency_matrix(
    ...     A, row_order=["u", "v"], column_order=["x", "y", "z"]
    ... )
    >>> sorted(G.edges(data="weight"))
    [('u', 'x', 1), ('u', 'z', 2), ('v', 'y', 3)]
    >>> G.nodes["u"]["bipartite"], G.nodes["x"]["bipartite"]
    (0, 1)

    Notes
    -----
    The nodes are labeled with the attribute `bipartite` set to an integer
    0 or 1 representing membership in part 0 or part 1 of the bipartite graph.

    If `create_using` is an instance of :class:`networkx.MultiGraph` or
    :class:`networkx.MultiDiGraph` and the entries of `A` are of
    type :class:`int`, then this function returns a multigraph (of the same
    type as `create_using`) with parallel edges. In this case, `edge_attribute`
    will be ignored.

    See Also
    --------
    biadjacency_matrix
    from_numpy_array

    References
    ----------
    [1] https://en.wikipedia.org/wiki/Adjacency_matrix#Adjacency_matrix_of_a_bipartite_graph
    """
    import scipy as sp

    if not sp.sparse.issparse(A):
        A = sp.sparse.coo_array(A)
    n, m = A.shape
    row_order = range(n) if row_order is None else list(row_order)
    column_order = range(n, n + m) if column_order is None else list(column_order)
    if len(row_order) != n:
        msg = f"row_order has {len(row_order)} nodes but A has {n} rows"
        raise _InvalidNodeOrder(msg)
    if len(column_order) != m:
        msg = f"column_order has {len(column_order)} nodes but A has {m} columns"
        raise _InvalidNodeOrder(msg)
    row_nodes = set(row_order)
    column_nodes = set(column_order)
    if len(row_nodes) != n:
        raise _InvalidNodeOrder("Ambiguous ordering: `row_order` contained duplicates.")
    if len(column_nodes) != m:
        msg = "Ambiguous ordering: `column_order` contained duplicates."
        raise _InvalidNodeOrder(msg)
    if not row_nodes.isdisjoint(column_nodes):
        msg = "row_order and column_order must not have nodes in common"
        raise _InvalidNodeOrder(msg)

    G = nx.empty_graph(0, create_using)
    # Make sure we get even the isolated nodes of the graph.
    G.add_nodes_from(row_order, bipartite=0)
    G.add_nodes_from(column_order, bipartite=1)
    # Create an iterable over (u, v, w) triples and for each triple, add an
    # edge from u to v with weight w.
    triples = (
        (row_order[u], column_order[v], d) for (u, v, d) in _generate_weighted_edges(A)
    )
    # If the entries in the adjacency matrix are integers and the graph is a
    # multigraph, then create parallel edges, each with weight 1, for each
    # entry in the adjacency matrix. Otherwise, create one edge for each
    # positive entry in the adjacency matrix and set the weight of that edge to
    # be the entry in the matrix.
    if A.dtype.kind in ("i", "u") and G.is_multigraph():
        chain = itertools.chain.from_iterable
        triples = chain(((u, v, 1) for d in range(w)) for (u, v, w) in triples)
    G.add_weighted_edges_from(triples, weight=edge_attribute)
    return G
