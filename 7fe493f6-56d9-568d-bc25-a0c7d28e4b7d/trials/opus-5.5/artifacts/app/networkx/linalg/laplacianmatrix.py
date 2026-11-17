"""Laplacian matrix of graphs.

All calculations here are done using the out-degree. For Laplacians using
in-degree, use `G.reverse(copy=False)` instead of `G` and take the transpose.

The `laplacian_matrix` function provides an unnormalized matrix,
while `normalized_laplacian_matrix`, `directed_laplacian_matrix`,
and `directed_combinatorial_laplacian_matrix` are all normalized.
"""

import networkx as nx
from networkx.utils import not_implemented_for

__all__ = [
    "laplacian_matrix",
    "normalized_laplacian_matrix",
    "magnetic_laplacian_matrix",
    "directed_laplacian_matrix",
    "directed_combinatorial_laplacian_matrix",
]


@nx._dispatchable(edge_attrs="weight")
def laplacian_matrix(G, nodelist=None, weight="weight"):
    """Returns the Laplacian matrix of G.

    The graph Laplacian is the matrix L = D - A, where
    A is the adjacency matrix and D is the diagonal matrix of node degrees.

    Parameters
    ----------
    G : graph
       A NetworkX graph

    nodelist : list, optional
       The rows and columns are ordered according to the nodes in nodelist.
       If nodelist is None, then the ordering is produced by G.nodes().

    weight : string or None, optional (default='weight')
       The edge data key used to compute each value in the matrix.
       If None, then each edge has weight 1.

    Returns
    -------
    L : SciPy sparse array
      The Laplacian matrix of G.

    Notes
    -----
    For MultiGraph, the edges weights are summed.

    This returns an unnormalized matrix. For a normalized output,
    use `normalized_laplacian_matrix`, `directed_laplacian_matrix`,
    or `directed_combinatorial_laplacian_matrix`.

    This calculation uses the out-degree of the graph `G`. To use the
    in-degree for calculations instead, use `G.reverse(copy=False)` and
    take the transpose.

    See Also
    --------
    :func:`~networkx.convert_matrix.to_numpy_array`
    normalized_laplacian_matrix
    directed_laplacian_matrix
    directed_combinatorial_laplacian_matrix
    :func:`~networkx.linalg.spectrum.laplacian_spectrum`

    Examples
    --------
    For graphs with multiple connected components, L is permutation-similar
    to a block diagonal matrix where each block is the respective Laplacian
    matrix for each component.

    >>> G = nx.Graph([(1, 2), (2, 3), (4, 5)])
    >>> print(nx.laplacian_matrix(G).toarray())
    [[ 1 -1  0  0  0]
     [-1  2 -1  0  0]
     [ 0 -1  1  0  0]
     [ 0  0  0  1 -1]
     [ 0  0  0 -1  1]]

    >>> edges = [
    ...     (1, 2),
    ...     (2, 1),
    ...     (2, 4),
    ...     (4, 3),
    ...     (3, 4),
    ... ]
    >>> DiG = nx.DiGraph(edges)
    >>> print(nx.laplacian_matrix(DiG).toarray())
    [[ 1 -1  0  0]
     [-1  2 -1  0]
     [ 0  0  1 -1]
     [ 0  0 -1  1]]

    Notice that node 4 is represented by the third column and row. This is because
    by default the row/column order is the order of `G.nodes` (i.e. the node added
    order -- in the edgelist, 4 first appears in (2, 4), before node 3 in edge (4, 3).)
    To control the node order of the matrix, use the `nodelist` argument.

    >>> print(nx.laplacian_matrix(DiG, nodelist=[1, 2, 3, 4]).toarray())
    [[ 1 -1  0  0]
     [-1  2  0 -1]
     [ 0  0  1 -1]
     [ 0  0 -1  1]]

    This calculation uses the out-degree of the graph `G`. To use the
    in-degree for calculations instead, use `G.reverse(copy=False)` and
    take the transpose.

    >>> print(nx.laplacian_matrix(DiG.reverse(copy=False)).toarray().T)
    [[ 1 -1  0  0]
     [-1  1 -1  0]
     [ 0  0  2 -1]
     [ 0  0 -1  1]]

    References
    ----------
    .. [1] Langville, Amy N., and Carl D. Meyer. Google’s PageRank and Beyond:
       The Science of Search Engine Rankings. Princeton University Press, 2006.

    """
    import scipy as sp

    if nodelist is None:
        nodelist = list(G)
    A = nx.to_scipy_sparse_array(G, nodelist=nodelist, weight=weight, format="csr")
    n, m = A.shape
    D = sp.sparse.dia_array((A.sum(axis=1), 0), shape=(m, n)).tocsr()
    return D - A


@nx._dispatchable(edge_attrs="weight")
def normalized_laplacian_matrix(G, nodelist=None, weight="weight"):
    r"""Returns the normalized Laplacian matrix of G.

    The normalized graph Laplacian is the matrix

    .. math::

        N = D^{-1/2} L D^{-1/2}

    where `L` is the graph Laplacian and `D` is the diagonal matrix of
    node degrees [1]_.

    Parameters
    ----------
    G : graph
       A NetworkX graph

    nodelist : list, optional
       The rows and columns are ordered according to the nodes in nodelist.
       If nodelist is None, then the ordering is produced by G.nodes().

    weight : string or None, optional (default='weight')
       The edge data key used to compute each value in the matrix.
       If None, then each edge has weight 1.

    Returns
    -------
    N : SciPy sparse array
      The normalized Laplacian matrix of G.

    Notes
    -----
    For MultiGraph, the edges weights are summed.
    See :func:`to_numpy_array` for other options.

    If the Graph contains selfloops, D is defined as ``diag(sum(A, 1))``, where A is
    the adjacency matrix [2]_.

    This calculation uses the out-degree of the graph `G`. To use the
    in-degree for calculations instead, use `G.reverse(copy=False)` and
    take the transpose.

    For an unnormalized output, use `laplacian_matrix`.

    Examples
    --------

    >>> import numpy as np
    >>> edges = [
    ...     (1, 2),
    ...     (2, 1),
    ...     (2, 4),
    ...     (4, 3),
    ...     (3, 4),
    ... ]
    >>> DiG = nx.DiGraph(edges)
    >>> print(nx.normalized_laplacian_matrix(DiG).toarray())
    [[ 1.         -0.70710678  0.          0.        ]
     [-0.70710678  1.         -0.70710678  0.        ]
     [ 0.          0.          1.         -1.        ]
     [ 0.          0.         -1.          1.        ]]

    Notice that node 4 is represented by the third column and row. This is because
    by default the row/column order is the order of `G.nodes` (i.e. the node added
    order -- in the edgelist, 4 first appears in (2, 4), before node 3 in edge (4, 3).)
    To control the node order of the matrix, use the `nodelist` argument.

    >>> print(nx.normalized_laplacian_matrix(DiG, nodelist=[1, 2, 3, 4]).toarray())
    [[ 1.         -0.70710678  0.          0.        ]
     [-0.70710678  1.          0.         -0.70710678]
     [ 0.          0.          1.         -1.        ]
     [ 0.          0.         -1.          1.        ]]
    >>> G = nx.Graph(edges)
    >>> print(nx.normalized_laplacian_matrix(G).toarray())
    [[ 1.         -0.70710678  0.          0.        ]
     [-0.70710678  1.         -0.5         0.        ]
     [ 0.         -0.5         1.         -0.70710678]
     [ 0.          0.         -0.70710678  1.        ]]

    See Also
    --------
    laplacian_matrix
    normalized_laplacian_spectrum
    directed_laplacian_matrix
    directed_combinatorial_laplacian_matrix

    References
    ----------
    .. [1] Fan Chung-Graham, Spectral Graph Theory,
       CBMS Regional Conference Series in Mathematics, Number 92, 1997.
    .. [2] Steve Butler, Interlacing For Weighted Graphs Using The Normalized
       Laplacian, Electronic Journal of Linear Algebra, Volume 16, pp. 90-98,
       March 2007.
    .. [3] Langville, Amy N., and Carl D. Meyer. Google’s PageRank and Beyond:
       The Science of Search Engine Rankings. Princeton University Press, 2006.
    """
    import numpy as np
    import scipy as sp

    if nodelist is None:
        nodelist = list(G)
    A = nx.to_scipy_sparse_array(G, nodelist=nodelist, weight=weight, format="csr")
    n, _ = A.shape
    diags = A.sum(axis=1)
    D = sp.sparse.dia_array((diags, 0), shape=(n, n)).tocsr()
    L = D - A
    with np.errstate(divide="ignore"):
        diags_sqrt = 1.0 / np.sqrt(diags)
    diags_sqrt[np.isinf(diags_sqrt)] = 0
    DH = sp.sparse.dia_array((diags_sqrt, 0), shape=(n, n)).tocsr()
    return DH @ (L @ DH)


@nx._dispatchable(edge_attrs="weight")
def magnetic_laplacian_matrix(
    G, *, nodelist=None, normalized=False, q=0.25, weight="weight"
):
    r"""Returns the magnetic Laplacian matrix of `G`.

    The magnetic Laplacian is a complex Hermitian matrix that encodes the
    direction of the edges of a (directed) graph in the phase of its
    off-diagonal entries [1]_ [2]_. With $A$ the weighted adjacency matrix,
    let

    .. math::

        A_s = \frac{1}{2}(A + A^T), \qquad
        \Theta^{(q)} = 2 \pi q (A - A^T), \qquad
        D_s = \operatorname{diag}(A_s \mathbf{1}).

    The magnetic Laplacian is

    .. math::

        L^{(q)} = D_s - A_s \odot \exp(i \Theta^{(q)}),

    where $\odot$ is the entry-wise product and the exponential is taken
    entry-wise. The normalized magnetic Laplacian is
    $D_s^{-1/2} L^{(q)} D_s^{-1/2}$, that is
    $I - D_s^{-1/2} \left(A_s \odot \exp(i \Theta^{(q)})\right) D_s^{-1/2}$
    for nodes with nonzero degree.

    An edge ``(u, v)`` without a reciprocal edge ``(v, u)`` contributes the
    phase $e^{2 \pi i q w}$ to entry ``(u, v)`` and the conjugate phase to
    entry ``(v, u)``, where $w$ is its weight. Reciprocal edges of equal
    weight, and hence all edges of undirected graphs, carry no phase.

    Parameters
    ----------
    G : graph
       A NetworkX graph

    nodelist : list, optional
       The rows and columns are ordered according to the nodes in `nodelist`.
       If `nodelist` is None, then the ordering is produced by ``G.nodes()``.

    normalized : bool, optional (default=False)
       If True, return the symmetrically normalized magnetic Laplacian
       $D_s^{-1/2} L^{(q)} D_s^{-1/2}$.

    q : float, optional (default=0.25)
       The charge parameter that sets the size of the phase. With ``q=0`` the
       magnetic Laplacian is the Laplacian of the symmetrized graph $A_s$.
       Values in ``[0, 1/2]`` cover all distinct behaviours for unweighted
       graphs and ``q=1/4`` maximally separates the two directions of an edge.

    weight : string or None, optional (default='weight')
       The edge data key used to compute each value in the matrix.
       If None, then each edge has weight 1.

    Returns
    -------
    L : SciPy sparse array
      The (complex, Hermitian) magnetic Laplacian matrix of `G`.

    Notes
    -----
    For MultiGraph/MultiDiGraph, the edges weights are summed.
    Self-loops contribute to $A_s$ and $D_s$ without a phase, so (as for
    :func:`laplacian_matrix`) they cancel on the diagonal of the
    unnormalized matrix.

    For undirected graphs the magnetic Laplacian equals the Laplacian
    (:func:`laplacian_matrix`) and its normalized version equals
    :func:`normalized_laplacian_matrix`, for every value of `q`.

    The magnetic Laplacian is positive semidefinite, so its eigenvalues are
    real and non-negative. See :func:`~networkx.linalg.spectrum.magnetic_spectrum`.

    Examples
    --------
    >>> import numpy as np
    >>> G = nx.DiGraph([(0, 1), (1, 2), (2, 0)])
    >>> L = nx.magnetic_laplacian_matrix(G)
    >>> print(np.round(L.toarray(), 6) + 0)
    [[1.+0.j  0.-0.5j 0.+0.5j]
     [0.+0.5j 1.+0.j  0.-0.5j]
     [0.-0.5j 0.+0.5j 1.+0.j ]]
    >>> np.allclose(L.toarray(), L.toarray().conj().T)  # Hermitian
    True

    Undirected graphs carry no phase:

    >>> H = nx.path_graph(4)
    >>> LH = nx.magnetic_laplacian_matrix(H)
    >>> np.allclose(LH.toarray(), nx.laplacian_matrix(H).toarray())
    True

    See Also
    --------
    laplacian_matrix
    normalized_laplacian_matrix
    magnetic_spectrum

    References
    ----------
    .. [1] M. Fanuel, C. M. Alaíz, Á. Fernández and J. A. K. Suykens,
       "Magnetic Eigenmaps for the Visualization of Directed Networks",
       Applied and Computational Harmonic Analysis, 44 (2018), pp. 189--199.
    .. [2] X. Zhang, Y. He, N. Brugnone, M. Perlmutter and M. Hirn,
       "MagNet: A Neural Network for Directed Graphs",
       Advances in Neural Information Processing Systems 34 (2021).
    """
    import numpy as np
    import scipy as sp

    if nodelist is None:
        nodelist = list(G)
    A = nx.to_scipy_sparse_array(
        G, nodelist=nodelist, weight=weight, dtype=float, format="coo"
    )
    n = A.shape[0]
    # Entries of A and of its transpose, on the union of both sparsity patterns.
    rows = np.concatenate((A.row, A.col))
    cols = np.concatenate((A.col, A.row))
    # A_s = (A + A^T) / 2 and the antisymmetric part A - A^T generating the phase.
    # Both are built from the same coordinates, so after summing duplicates
    # their entries are stored in the same (canonical) order.
    sym = sp.sparse.coo_array(
        (np.concatenate((A.data, A.data)) / 2, (rows, cols)), shape=(n, n)
    )
    antisym = sp.sparse.coo_array(
        (np.concatenate((A.data, -A.data)), (rows, cols)), shape=(n, n)
    )
    sym.sum_duplicates()
    antisym.sum_duplicates()
    phase = np.exp(2j * np.pi * q * antisym.data)
    H = sp.sparse.coo_array((sym.data * phase, (sym.row, sym.col)), shape=(n, n))
    diags = sym.sum(axis=1)
    D = sp.sparse.dia_array((diags, 0), shape=(n, n))
    L = (D - H).tocsr()
    if not normalized:
        return L
    with np.errstate(divide="ignore"):
        diags_sqrt = 1.0 / np.sqrt(diags)
    diags_sqrt[np.isinf(diags_sqrt)] = 0
    DH = sp.sparse.dia_array((diags_sqrt, 0), shape=(n, n)).tocsr()
    return DH @ (L @ DH)


###############################################################################
# Code based on work from https://github.com/bjedwards


@not_implemented_for("undirected")
@not_implemented_for("multigraph")
@nx._dispatchable(edge_attrs="weight")
def directed_laplacian_matrix(
    G, nodelist=None, weight="weight", walk_type=None, alpha=0.95
):
    r"""Returns the directed Laplacian matrix of G.

    The graph directed Laplacian is the matrix

    .. math::

        L = I - \frac{1}{2} \left (\Phi^{1/2} P \Phi^{-1/2} + \Phi^{-1/2} P^T \Phi^{1/2} \right )

    where `I` is the identity matrix, `P` is the transition matrix of the
    graph, and `\Phi` a matrix with the Perron vector of `P` in the diagonal and
    zeros elsewhere [1]_.

    Depending on the value of walk_type, `P` can be the transition matrix
    induced by a random walk, a lazy random walk, or a random walk with
    teleportation (PageRank).

    Parameters
    ----------
    G : DiGraph
       A NetworkX graph

    nodelist : list, optional
       The rows and columns are ordered according to the nodes in nodelist.
       If nodelist is None, then the ordering is produced by G.nodes().

    weight : string or None, optional (default='weight')
       The edge data key used to compute each value in the matrix.
       If None, then each edge has weight 1.

    walk_type : string or None, optional (default=None)
       One of ``"random"``, ``"lazy"``, or ``"pagerank"``. If ``walk_type=None``
       (the default), then a value is selected according to the properties of `G`:
       - ``walk_type="random"`` if `G` is strongly connected and aperiodic
       - ``walk_type="lazy"`` if `G` is strongly connected but not aperiodic
       - ``walk_type="pagerank"`` for all other cases.

    alpha : real
       (1 - alpha) is the teleportation probability used with pagerank

    Returns
    -------
    L : NumPy matrix
      Normalized Laplacian of G.

    Notes
    -----
    Only implemented for DiGraphs

    The result is always a symmetric matrix.

    This calculation uses the out-degree of the graph `G`. To use the
    in-degree for calculations instead, use `G.reverse(copy=False)` and
    take the transpose.

    See Also
    --------
    laplacian_matrix
    normalized_laplacian_matrix
    directed_combinatorial_laplacian_matrix

    References
    ----------
    .. [1] Fan Chung (2005).
       Laplacians and the Cheeger inequality for directed graphs.
       Annals of Combinatorics, 9(1), 2005
    """
    import numpy as np
    import scipy as sp

    # NOTE: P has type ndarray if walk_type=="pagerank", else csr_array
    P = _transition_matrix(
        G, nodelist=nodelist, weight=weight, walk_type=walk_type, alpha=alpha
    )

    n, m = P.shape

    evals, evecs = sp.sparse.linalg.eigs(P.T, k=1)
    v = evecs.flatten().real
    p = v / v.sum()
    # p>=0 by Perron-Frobenius Thm. Use abs() to fix roundoff across zero gh-6865
    sqrtp = np.sqrt(np.abs(p))
    Q = (
        sp.sparse.dia_array((sqrtp, 0), shape=(n, n)).tocsr()
        @ P
        @ sp.sparse.dia_array((1.0 / sqrtp, 0), shape=(n, n)).tocsr()
    )
    # NOTE: This could be sparsified for the non-pagerank cases
    I = np.identity(len(G))

    return I - (Q + Q.T) / 2.0


@not_implemented_for("undirected")
@not_implemented_for("multigraph")
@nx._dispatchable(edge_attrs="weight")
def directed_combinatorial_laplacian_matrix(
    G, nodelist=None, weight="weight", walk_type=None, alpha=0.95
):
    r"""Return the directed combinatorial Laplacian matrix of G.

    The graph directed combinatorial Laplacian is the matrix

    .. math::

        L = \Phi - \frac{1}{2} \left (\Phi P + P^T \Phi \right)

    where `P` is the transition matrix of the graph and `\Phi` a matrix
    with the Perron vector of `P` in the diagonal and zeros elsewhere [1]_.

    Depending on the value of walk_type, `P` can be the transition matrix
    induced by a random walk, a lazy random walk, or a random walk with
    teleportation (PageRank).

    Parameters
    ----------
    G : DiGraph
       A NetworkX graph

    nodelist : list, optional
       The rows and columns are ordered according to the nodes in nodelist.
       If nodelist is None, then the ordering is produced by G.nodes().

    weight : string or None, optional (default='weight')
       The edge data key used to compute each value in the matrix.
       If None, then each edge has weight 1.

    walk_type : string or None, optional (default=None)
        One of ``"random"``, ``"lazy"``, or ``"pagerank"``. If ``walk_type=None``
        (the default), then a value is selected according to the properties of `G`:
        - ``walk_type="random"`` if `G` is strongly connected and aperiodic
        - ``walk_type="lazy"`` if `G` is strongly connected but not aperiodic
        - ``walk_type="pagerank"`` for all other cases.

    alpha : real
       (1 - alpha) is the teleportation probability used with pagerank

    Returns
    -------
    L : NumPy matrix
      Combinatorial Laplacian of G.

    Notes
    -----
    Only implemented for DiGraphs

    The result is always a symmetric matrix.

    This calculation uses the out-degree of the graph `G`. To use the
    in-degree for calculations instead, use `G.reverse(copy=False)` and
    take the transpose.

    See Also
    --------
    laplacian_matrix
    normalized_laplacian_matrix
    directed_laplacian_matrix

    References
    ----------
    .. [1] Fan Chung (2005).
       Laplacians and the Cheeger inequality for directed graphs.
       Annals of Combinatorics, 9(1), 2005
    """
    import scipy as sp

    P = _transition_matrix(
        G, nodelist=nodelist, weight=weight, walk_type=walk_type, alpha=alpha
    )

    n, m = P.shape

    evals, evecs = sp.sparse.linalg.eigs(P.T, k=1)
    v = evecs.flatten().real
    p = v / v.sum()
    # NOTE: could be improved by not densifying
    Phi = sp.sparse.dia_array((p, 0), shape=(n, n)).toarray()

    return Phi - (Phi @ P + P.T @ Phi) / 2.0


def _transition_matrix(G, nodelist=None, weight="weight", walk_type=None, alpha=0.95):
    """Returns the transition matrix of G.

    This is a row stochastic giving the transition probabilities while
    performing a random walk on the graph. Depending on the value of walk_type,
    P can be the transition matrix induced by a random walk, a lazy random walk,
    or a random walk with teleportation (PageRank).

    Parameters
    ----------
    G : DiGraph
       A NetworkX graph

    nodelist : list, optional
       The rows and columns are ordered according to the nodes in nodelist.
       If nodelist is None, then the ordering is produced by G.nodes().

    weight : string or None, optional (default='weight')
       The edge data key used to compute each value in the matrix.
       If None, then each edge has weight 1.

    walk_type : string or None, optional (default=None)
       One of ``"random"``, ``"lazy"``, or ``"pagerank"``. If ``walk_type=None``
       (the default), then a value is selected according to the properties of `G`:
        - ``walk_type="random"`` if `G` is strongly connected and aperiodic
        - ``walk_type="lazy"`` if `G` is strongly connected but not aperiodic
        - ``walk_type="pagerank"`` for all other cases.

    alpha : real
       (1 - alpha) is the teleportation probability used with pagerank

    Returns
    -------
    P : numpy.ndarray
      transition matrix of G.

    Raises
    ------
    NetworkXError
        If walk_type not specified or alpha not in valid range
    """
    import numpy as np
    import scipy as sp

    if walk_type is None:
        if nx.is_strongly_connected(G):
            if nx.is_aperiodic(G):
                walk_type = "random"
            else:
                walk_type = "lazy"
        else:
            walk_type = "pagerank"

    A = nx.to_scipy_sparse_array(G, nodelist=nodelist, weight=weight, dtype=float)
    n, m = A.shape
    if walk_type in ["random", "lazy"]:
        DI = sp.sparse.dia_array((1.0 / A.sum(axis=1), 0), shape=(n, n)).tocsr()
        if walk_type == "random":
            P = DI @ A
        else:
            I = sp.sparse.eye_array(n, format="csr")
            P = (I + DI @ A) / 2.0

    elif walk_type == "pagerank":
        if not (0 < alpha < 1):
            raise nx.NetworkXError("alpha must be between 0 and 1")
        # this is using a dense representation. NOTE: This should be sparsified!
        A = A.toarray()
        # add constant to dangling nodes' row
        A[A.sum(axis=1) == 0, :] = 1 / n
        # normalize
        A = A / A.sum(axis=1)[np.newaxis, :].T
        P = alpha * A + (1 - alpha) / n
    else:
        raise nx.NetworkXError("walk_type must be random, lazy, or pagerank")

    return P
