"""
Eigenvalue spectrum of graphs.
"""

import networkx as nx

__all__ = [
    "laplacian_spectrum",
    "adjacency_spectrum",
    "modularity_spectrum",
    "normalized_laplacian_spectrum",
    "magnetic_spectrum",
    "bethe_hessian_spectrum",
]


@nx._dispatchable(edge_attrs="weight")
def laplacian_spectrum(G, weight="weight"):
    """Returns eigenvalues of the Laplacian of G

    Parameters
    ----------
    G : graph
       A NetworkX graph

    weight : string or None, optional (default='weight')
       The edge data key used to compute each value in the matrix.
       If None, then each edge has weight 1.

    Returns
    -------
    evals : NumPy array
      Eigenvalues

    Notes
    -----
    For MultiGraph/MultiDiGraph, the edges weights are summed.
    See :func:`~networkx.convert_matrix.to_numpy_array` for other options.

    See Also
    --------
    laplacian_matrix

    Examples
    --------
    The multiplicity of 0 as an eigenvalue of the laplacian matrix is equal
    to the number of connected components of G.

    >>> G = nx.Graph()  # Create a graph with 5 nodes and 3 connected components
    >>> G.add_nodes_from(range(5))
    >>> G.add_edges_from([(0, 2), (3, 4)])
    >>> nx.laplacian_spectrum(G)
    array([0., 0., 0., 2., 2.])

    """
    import scipy as sp

    return sp.linalg.eigvalsh(nx.laplacian_matrix(G, weight=weight).todense())


@nx._dispatchable(edge_attrs="weight")
def normalized_laplacian_spectrum(G, weight="weight"):
    """Return eigenvalues of the normalized Laplacian of G

    Parameters
    ----------
    G : graph
       A NetworkX graph

    weight : string or None, optional (default='weight')
       The edge data key used to compute each value in the matrix.
       If None, then each edge has weight 1.

    Returns
    -------
    evals : NumPy array
      Eigenvalues

    Notes
    -----
    For MultiGraph/MultiDiGraph, the edges weights are summed.
    See to_numpy_array for other options.

    See Also
    --------
    normalized_laplacian_matrix
    """
    import scipy as sp

    return sp.linalg.eigvalsh(
        nx.normalized_laplacian_matrix(G, weight=weight).todense()
    )


@nx._dispatchable(edge_attrs="weight")
def magnetic_spectrum(G, *, q=0.25, weight="weight", normalized=False):
    """Returns eigenvalues of the magnetic Laplacian of G.

    The magnetic Laplacian is Hermitian and positive semidefinite, so its
    eigenvalues are real and non-negative. They are returned in ascending
    order.

    Parameters
    ----------
    G : graph
       A NetworkX graph

    q : float, optional (default=0.25)
       The charge parameter of the magnetic Laplacian, which sets the size of
       the phase carried by directed edges.

    weight : string or None, optional (default='weight')
       The edge data key used to compute each value in the matrix.
       If None, then each edge has weight 1.

    normalized : bool, optional (default=False)
       If True, return the eigenvalues of the normalized magnetic Laplacian.

    Returns
    -------
    evals : NumPy array
      Real eigenvalues in ascending order.

    Notes
    -----
    For MultiGraph/MultiDiGraph, the edges weights are summed.

    For undirected graphs the magnetic spectrum equals the Laplacian
    spectrum (or the normalized Laplacian spectrum when `normalized` is True)
    for every value of `q`.

    See Also
    --------
    magnetic_laplacian_matrix
    laplacian_spectrum
    normalized_laplacian_spectrum

    Examples
    --------
    A directed 3-cycle has a zero eigenvalue only when the phases around the
    cycle add up to a multiple of $2\\pi$, e.g. for ``q=1/3``:

    >>> G = nx.DiGraph([(0, 1), (1, 2), (2, 0)])
    >>> evals = nx.magnetic_spectrum(G, q=1 / 3)
    >>> [round(float(ev), 6) + 0 for ev in evals]
    [0.0, 1.5, 1.5]
    >>> [round(float(ev), 6) for ev in nx.magnetic_spectrum(G)]
    [0.133975, 1.0, 1.866025]
    """
    import scipy as sp

    L = nx.magnetic_laplacian_matrix(G, q=q, weight=weight, normalized=normalized)
    return sp.linalg.eigvalsh(L.todense())


@nx._dispatchable(edge_attrs="weight")
def adjacency_spectrum(G, weight="weight"):
    """Returns eigenvalues of the adjacency matrix of G.

    Parameters
    ----------
    G : graph
       A NetworkX graph

    weight : string or None, optional (default='weight')
       The edge data key used to compute each value in the matrix.
       If None, then each edge has weight 1.

    Returns
    -------
    evals : NumPy array
      Eigenvalues

    Notes
    -----
    For MultiGraph/MultiDiGraph, the edges weights are summed.
    See to_numpy_array for other options.

    See Also
    --------
    adjacency_matrix
    """
    import scipy as sp

    return sp.linalg.eigvals(nx.adjacency_matrix(G, weight=weight).todense())


@nx._dispatchable
def modularity_spectrum(G):
    """Returns eigenvalues of the modularity matrix of G.

    Parameters
    ----------
    G : Graph
       A NetworkX Graph or DiGraph

    Returns
    -------
    evals : NumPy array
      Eigenvalues

    See Also
    --------
    modularity_matrix

    References
    ----------
    .. [1] M. E. J. Newman, "Modularity and community structure in networks",
       Proc. Natl. Acad. Sci. USA, vol. 103, pp. 8577-8582, 2006.
    """
    import scipy as sp

    if G.is_directed():
        return sp.linalg.eigvals(nx.directed_modularity_matrix(G))
    else:
        return sp.linalg.eigvals(nx.modularity_matrix(G))


@nx._dispatchable
def bethe_hessian_spectrum(G, r=None):
    """Returns eigenvalues of the Bethe Hessian matrix of G.

    Parameters
    ----------
    G : Graph
       A NetworkX Graph or DiGraph

    r : float
       Regularizer parameter

    Returns
    -------
    evals : NumPy array
      Eigenvalues

    See Also
    --------
    bethe_hessian_matrix

    References
    ----------
    .. [1] A. Saade, F. Krzakala and L. Zdeborová
       "Spectral clustering of graphs with the bethe hessian",
       Advances in Neural Information Processing Systems. 2014.
    """
    import scipy as sp

    return sp.linalg.eigvalsh(nx.bethe_hessian_matrix(G, r).todense())
