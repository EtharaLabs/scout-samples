"""
PyTorch code printer

The :class:`TorchPrinter` converts SymPy expressions into code that evaluates
them with `PyTorch <https://pytorch.org>`_ tensors. It is used by ``lambdify``
when ``modules='torch'`` is given.
"""
from collections.abc import Iterable

import sympy
from sympy.codegen.cfunctions import Sqrt
from sympy.core.mul import Mul
from sympy.core.numbers import Integer
from sympy.core.singleton import S
from sympy.external import import_module
from sympy.matrices.expressions import MatrixExpr
from sympy.printing.precedence import PRECEDENCE
from sympy.printing.pycode import AbstractPythonCodePrinter, ArrayPrinter


class TorchPrinter(ArrayPrinter, AbstractPythonCodePrinter):
    """
    PyTorch printer which handles vectorized piecewise functions,
    logical operators, max/min, matrix operations and derivatives
    (through ``torch.autograd``).

    Settings
    ========

    requires_grad : bool
        Whether explicit matrices are created as tensors which require
        gradients. Default is ``False``.
    dtype : str
        The ``dtype`` of tensors created from explicit matrices. Default is
        ``"torch.float64"``.
    torch_version : str
        The version of PyTorch to generate code for. By default the
        installed version is used, if any.

    Examples
    ========

    >>> from sympy import sin, sqrt, Matrix
    >>> from sympy.abc import x
    >>> from sympy.printing.pytorch import torch_code
    >>> torch_code(sin(x) + sqrt(x))
    'torch.sqrt(x) + torch.sin(x)'
    >>> torch_code(Matrix([[1, 2], [3, 4]]))
    'torch.tensor([[1, 2], [3, 4]], dtype=torch.float64)'
    >>> torch_code(Matrix([[1, 2], [3, 4]]), requires_grad=True, dtype="torch.float32")
    'torch.tensor([[1, 2], [3, 4]], dtype=torch.float32, requires_grad=True)'
    """

    printmethod = "_torchcode"
    language = "Python with PyTorch"

    mapping = {
        sympy.Abs: "torch.abs",
        sympy.sign: "torch.sign",

        # XXX May raise error for ints.
        sympy.ceiling: "torch.ceil",
        sympy.floor: "torch.floor",
        sympy.log: "torch.log",
        sympy.exp: "torch.exp",
        Sqrt: "torch.sqrt",
        sympy.cos: "torch.cos",
        sympy.acos: "torch.acos",
        sympy.sin: "torch.sin",
        sympy.asin: "torch.asin",
        sympy.tan: "torch.tan",
        sympy.atan: "torch.atan",
        sympy.atan2: "torch.atan2",
        # XXX Also may give NaN for complex results.
        sympy.cosh: "torch.cosh",
        sympy.acosh: "torch.acosh",
        sympy.sinh: "torch.sinh",
        sympy.asinh: "torch.asinh",
        sympy.tanh: "torch.tanh",
        sympy.atanh: "torch.atanh",

        sympy.re: "torch.real",
        sympy.im: "torch.imag",
        sympy.arg: "torch.angle",

        # XXX May raise error for ints and complexes
        sympy.erf: "torch.erf",
        sympy.loggamma: "torch.lgamma",

        sympy.Eq: "torch.eq",
        sympy.Ne: "torch.ne",
        sympy.StrictGreaterThan: "torch.gt",
        sympy.StrictLessThan: "torch.lt",
        sympy.LessThan: "torch.le",
        sympy.GreaterThan: "torch.ge",

        sympy.And: "torch.logical_and",
        sympy.Or: "torch.logical_or",
        sympy.Not: "torch.logical_not",
        sympy.Max: "torch.maximum",
        sympy.Min: "torch.minimum",

        # Matrices
        sympy.MatAdd: "torch.add",
        sympy.HadamardProduct: "torch.mul",
        sympy.Trace: "torch.trace",

        # XXX May raise error for integer matrices.
        sympy.Determinant: "torch.det",
    }

    _default_settings = dict(
        AbstractPythonCodePrinter._default_settings,
        torch_version=None,
        requires_grad=False,
        dtype="torch.float64",
    )

    def __init__(self, settings=None):
        super().__init__(settings)

        version = self._settings['torch_version']
        if version is None:
            # imported here so that importing this module does not import torch
            torch = import_module('torch')
            if torch:
                version = torch.__version__
        self.torch_version = version
        self.requires_grad = self._settings['requires_grad']
        self.dtype = self._settings['dtype']

    def _print_Function(self, expr):
        op = self.mapping.get(type(expr), None)
        if op is None:
            return super()._print_Basic(expr)
        children = [self._print(arg) for arg in expr.args]
        if len(children) == 1:
            return "%s(%s)" % (
                self._module_format(op),
                children[0]
            )
        else:
            return self._expand_fold_binary_op(op, children)

    # mirrors the tensorflow printer
    _print_Expr = _print_Function
    _print_Application = _print_Function
    _print_MatrixExpr = _print_Function
    _print_Relational = _print_Function
    _print_Not = _print_Function
    _print_And = _print_Function
    _print_Or = _print_Function
    _print_HadamardProduct = _print_Function
    _print_Trace = _print_Function
    _print_Determinant = _print_Function

    def _print_Inverse(self, expr):
        return "{}({})".format(self._module_format("torch.linalg.inv"),
                               self._print(expr.args[0]))

    def _print_Transpose(self, expr):
        # swap the last two dimensions, i.e. transpose the matrices
        return "{}({}, -2, -1)".format(self._module_format("torch.transpose"),
                                       self._print(expr.arg))

    def _print_PermuteDims(self, expr):
        return "%s.permute(%s)" % (
            self.parenthesize(expr.expr, PRECEDENCE["Atom"], strict=True),
            ", ".join(str(i) for i in expr.permutation.array_form)
        )

    def _print_Derivative(self, expr):
        # Derivatives are computed with automatic differentiation: the
        # variables have to be tensors created with requires_grad=True.
        result = self._print(expr.expr)
        for var, order in expr.variable_count:
            if isinstance(var, Iterable) or not isinstance(order, (int, Integer)):
                raise NotImplementedError(
                    "only derivatives with respect to scalars of integer order are supported")
            for _ in range(int(order)):
                result = "{}({}, {}, create_graph=True)[0]".format(
                    self._module_format("torch.autograd.grad"),
                    result, self._print(var))
        return result

    def _print_Piecewise(self, expr):
        from sympy.functions.elementary.piecewise import Piecewise
        e, cond = expr.args[0].args
        if len(expr.args) == 1:
            return '{}({}, {}, {})'.format(
                self._module_format("torch.where"),
                self._print(cond),
                self._print(e),
                0)

        return '{}({}, {}, {})'.format(
            self._module_format("torch.where"),
            self._print(cond),
            self._print(e),
            self._print(Piecewise(*expr.args[1:])))

    def _print_Pow(self, expr):
        # XXX May raise error for
        # int**float or int**complex or float**complex
        base, exp = expr.args
        if expr.exp == S.Half:
            return "{}({})".format(
                self._module_format("torch.sqrt"), self._print(base))
        return "{}({}, {})".format(
            self._module_format("torch.pow"),
            self._print(base), self._print(exp))

    def _print_MatMul(self, expr):
        # Separate matrix and scalar arguments
        mat_args = [arg for arg in expr.args if isinstance(arg, MatrixExpr)]
        args = [arg for arg in expr.args if arg not in mat_args]
        if args:
            return "%s*%s" % (
                self.parenthesize(Mul.fromiter(args), PRECEDENCE["Mul"]),
                self._expand_fold_binary_op("torch.matmul", mat_args)
            )
        else:
            return self._expand_fold_binary_op("torch.matmul", mat_args)

    def _print_MatPow(self, expr):
        if not expr.exp.is_Integer:
            raise NotImplementedError(
                "only integer powers of matrices are supported")
        # matrix_power also handles negative powers (through the inverse)
        return "{}({}, {})".format(
            self._module_format("torch.linalg.matrix_power"),
            self._print(expr.base), self._print(expr.exp))

    def _print_MatrixBase(self, expr):
        data = "[" + ", ".join(["[" + ", ".join([self._print(j) for j in i]) + "]"
                                for i in expr.tolist()]) + "]"
        params = [data, "dtype={}".format(self.dtype)]
        if self.requires_grad:
            params.append("requires_grad=True")
        return "{}({})".format(self._module_format("torch.tensor"),
                               ", ".join(params))

    def _print_isnan(self, expr):
        return "{}({})".format(self._module_format("torch.isnan"),
                               self._print(expr.args[0]))

    def _print_isinf(self, expr):
        return "{}({})".format(self._module_format("torch.isinf"),
                               self._print(expr.args[0]))

    def _print_Identity(self, expr):
        rows, cols = expr.shape
        if rows == cols:
            return "{}({})".format(self._module_format("torch.eye"),
                                   self._print(rows))
        return "{}({}, {})".format(self._module_format("torch.eye"),
                                   self._print(rows), self._print(cols))

    def _print_ZeroMatrix(self, expr):
        return "{}({})".format(self._module_format("torch.zeros"),
                               self._print(expr.shape))

    def _print_OneMatrix(self, expr):
        return "{}({})".format(self._module_format("torch.ones"),
                               self._print(expr.shape))

    def _print_conjugate(self, expr):
        return "{}({})".format(self._module_format("torch.conj"),
                               self._print(expr.args[0]))

    def _print_ImaginaryUnit(self, expr):
        return "1j"

    def _print_Heaviside(self, expr):
        # SymPy's default value at zero is 1/2
        H0 = expr.args[1] if len(expr.args) > 1 else S.Half
        return "{}({}, {}({}))".format(
            self._module_format("torch.heaviside"),
            self._print(expr.args[0]),
            self._module_format("torch.tensor"),
            self._print(H0))

    def _print_gamma(self, expr):
        # torch has no gamma function, but exp(lgamma(x)) is |gamma(x)|
        # which agrees with gamma(x) for positive x
        return "{}({}({}))".format(self._module_format("torch.exp"),
                                   self._module_format("torch.lgamma"),
                                   self._print(expr.args[0]))

    def _print_polygamma(self, expr):
        return "{}({}, {})".format(self._module_format("torch.special.polygamma"),
                                   self._print(expr.args[0]),
                                   self._print(expr.args[1]))

    def _print_CodeBlock(self, expr):
        return "\n".join(self._print(subexpr) for subexpr in expr.args)

    _module = "torch"
    _einsum = "einsum"
    _add = "add"
    _transpose = "t"
    _ones = "ones"
    _zeros = "zeros"


def torch_code(expr, requires_grad=False, dtype=None):
    """Convert ``expr`` to a string of PyTorch code.

    Parameters
    ==========

    expr : Expr
        The expression to convert.
    requires_grad : bool, optional
        Whether tensors created from explicit matrices require gradients.
        Default is ``False``.
    dtype : str, optional
        The ``dtype`` of tensors created from explicit matrices, e.g.
        ``"torch.float32"``. Default is ``"torch.float64"``.

    Examples
    ========

    >>> from sympy import exp, Piecewise
    >>> from sympy.abc import x
    >>> from sympy.printing.pytorch import torch_code
    >>> torch_code(exp(-x**2))
    'torch.exp(-torch.pow(x, 2))'
    >>> torch_code(Piecewise((x, x < 0), (x**2, True)))
    'torch.where(torch.lt(x, 0), x, torch.pow(x, 2))'
    """
    settings = {'requires_grad': requires_grad}
    if dtype is not None:
        settings['dtype'] = dtype
    printer = TorchPrinter(settings)
    return printer.doprint(expr)
