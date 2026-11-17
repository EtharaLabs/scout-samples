# Evolve the expression core, the functions, the number theory and the printers

The repository is pinned at a revision that predates a later release. Your task is to make the
behaviour that release describes appear, without regressing the 4946 tests that already pass. The
objectives below are the release's own scope restated. They are numbered for reference only.

You are not given the release tag, any pull request number, or any diff. Derive the change list from
the objectives and the repository.

This library keeps its tests **inside** the package, under `sympy/**/tests/`. Change only files
under `sympy/`, and do not modify any of those 65 test subtrees: each is replaced with the later
release's version before your work is exercised, so edits to them have no effect.

**This is the most broadly distributed task in its family.** The work spreads over 31 files and 31
behavioural areas, and no file and no area dominates. Sixteen areas rest on a single test each.
There is no insight that unlocks a large fraction of this task; there are fourteen mostly
independent pieces of work, several of them small.

The disclosed-interfaces table below carries the names this release invents. Five test modules in
this cluster cannot be imported at all until the names they import exist, so withholding them would
measure whether you can guess an identifier rather than whether you can implement behaviour. Naming
them is not sufficient on its own: each must carry the behaviour described. Only behaviour counts.

Everything else must be derived from the repository and from what the tests assert. This release's
work is overwhelmingly conduct behind interfaces the pinned revision already exports.

## Disclosed interfaces

Every symbol below is created by this release and appears nowhere in the source tree you
received, so no amount of reading could recover its name. The suite imports each exactly as
written: correct behaviour behind a different name or arity does not satisfy them. Symbols this
release changes that ALREADY exist in your tree are deliberately not listed; find those yourself.
A name on its own is not enough: each symbol must carry the behaviour described below.

| Module | Symbol | Parameters | Returns |
| --- | --- | --- | --- |
| `sympy.core.basic` | `subs` | self, arg1, arg2=None, **kwargs | the substituted expression. The signature CHANGES: the release names the first two arguments explicitly where the base revision took them from *args.  |
| `sympy.core.function` | `DefinedFunction` | class, subclass of Function | the base class that library-defined functions derive from, separating them from user-defined ones. The core's class-registration test asserts it is constructible and registered, and the elementary and special function hierarchies are expected to sit under it. |
| `sympy.ntheory.factor_` | `FactorCache` | class | the cache type backing repeated factorisation. A module-level instance named `factor_cache` is also expected: the release's own test imports that exact lowercase name from this module, so both the class and the instance are part of the surface. |
| `sympy.ntheory.qs` | `qs_factor` | N, prime_bound, M, ERROR_TERM=25, seed=1234 | the factorisation of N as a mapping of prime to multiplicity, where the existing `qs` returns a set of factors. Note the five positional parameters and the two defaults. It must also be re-exported from the `sympy.ntheory` package namespace, because the test imports it from there rather than from this module. |
| `sympy.ntheory.qs` | `_generate_polynomial` | (private, imported by name) | a private helper the release's own test module imports by exact name alongside the public entry points. It is disclosed for that reason only; its contract is whatever the tests that exercise it require. |
| `sympy.printing.pycode` | `CmathPrinter` | class, a code printer | a printer emitting expressions against the C math library's complex functions. It lives in the Python-code printing module rather than the C one, which is where the test imports it from. |
| `sympy.printing.pytorch` | `TorchPrinter, torch_code` | TorchPrinter is a class; torch_code(expr, requires_grad=False, dtype=None) | a printer and a convenience entry point for a tensor framework, in a NEW module. The tensor framework itself is NOT installed in this environment, so this module's behaviour cannot be exercised here; it is disclosed because the module is part of the release's surface and the package namespace references it. |

## Objectives

**1. Factoring by quadratic sieve returns multiplicities.** Alongside the existing sieve entry point
that yields a set of factors, provide one that yields the full factorisation as a mapping from prime
to multiplicity, seedable and parameterised by the prime bound, the sieve interval and an error term.
It must be reachable from the number-theory package namespace, not only from its own module. This is
the largest objective, five tests, and it also exercises the sieve's polynomial generation directly.

**2. Factorisation is cached.** Integer factorisation gains a cache object, exposed both as a type and
as a module-level instance that the suite imports by name. Perfect-power detection is corrected in the
same area.

**3. Adjoint, transpose and conjugate behave on matrix expressions and operators.** The three unary
operations must compose correctly, respect each other's identities, and work when the operand is an
operator rather than a plain matrix. Whether a matrix expression reports itself hermitian must follow
from its structure.

**4. Series expansion works through the function interface.** A function defined through the public
interface must expand to a series correctly, in three cases the suite distinguishes.

**5. Three corrections in the expression core.** Dividing a float by zero must raise rather than
produce a silent value; an unevaluated product must keep its unevaluated structure; and replacing a
subexpression inside an integral must reach into the integral rather than stopping at it.

**6. Substitution and rewriting on the base class.** The substitution entry point on the base
expression class takes its first two arguments explicitly rather than from a variadic list, and all
three call shapes must keep working: a single mapping, a single sequence of pairs, and two separate
arguments. Rewriting an absolute value is corrected in the same class.

**7. Assumptions resolve consistently.** The common assumptions must hold across the classes that
declare them, and the assumptions that are expected to fail must fail rather than erroring.

**8. Modular arithmetic and hermitian products.** The modulo operation is corrected, and a product of
hermitian and antihermitian factors must report the right character.

**9. Two combinatorial numbers.** Euler polynomials and the partition function must evaluate as the
suite asserts.

**10. Floor and ceiling on integers.** Both must behave for the integer cases the suite covers.

**11. A base class for library-defined functions.** The core gains a class that library-defined
functions derive from, distinguishing them from user-defined ones. It must be constructible and must
appear in the core's class registry, and the function hierarchy is expected to sit under it.

**12. The code printers.** This is the broadest objective, thirteen tests across ten printers. A new
printer targets the C math library's complex functions and lives in the Python-code printing module.
The Python, C89, Julia, Mathematica and Rust printers each have a case to fix, as do the NumPy and
JAX array printers and the lambda representation of multiple sums. LaTeX must print a dot product and
must honour the option that disables splitting super- and subscripts. Operator precedence must compare
correctly for a user-defined function.

**13. The parser.** Exclusive-or must evaluate as the suite expects, and one further parsing case is
corrected.

**14. Seven smaller corrections.** The extended greatest-common-divisor routine, replacing a
relational inside a piecewise expression, one power case, pattern matching against a bound symbol, a
residue computation, one matrix-base case, and solving a linear system whose entries do not commute.

Objectives 1, 2, 11 and the new printer in 12 add surface, and their names are disclosed. Everything
else changes conduct behind interfaces that already exist, and for those you must read what the tests
assert.

One trap is worth stating. Five of this cluster's test modules fail to import at the pinned
revision, and a module that cannot import exercises nothing at all. Creating the names they want
will make them collect, and the suite's pass count will jump. That jump means only that collection
was restored, not that behaviour changed. Required behaviour is what matters.

## Constraints

Change only files under `sympy/`. Do not modify files under any `tests/` subtree; those are restored
from the release before your work is exercised, so edits to them have no effect.

Complete objectives rather than spreading partial repairs across all of them. A change that
satisfies one objective by breaking another is not an improvement.
