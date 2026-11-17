---
name: sympy-114-port-status
description: "Status of porting SymPy 1.14 behaviours into the /app sympy 1.14.dev tree (what was done, what could not be identified)"
metadata:
  node_type: memory
  type: project
  originSessionId: c0041597-4015-4501-aeab-64e604f12727
  modified: 2026-11-17T08:58:36.939Z
---

Task (2026-11-17): make /app (sympy 1.14.dev) exhibit 1.14 behaviours; tests under sympy/**/tests are replaced by 1.14's, so only non-test files were changed.

Done: DefinedFunction (+ all library functions subclass it), Basic.subs(arg1, arg2=None), qs rewrite + qs_factor/_generate_polynomial (bit-vector smoothness, verified against remembered 1.14 test values), FactorCache/factor_cache (+factorint integration), perfect_power negatives/rationals, CmathPrinter, pytorch.py TorchPrinter/torch_code, lambdify 'cmath'/'torch', many printer fixes (C89 Mod, Mathematica, Rust, NumPy/JAX zoo, LaTeX DotProduct + disable_split_super_sub, Sum loop order, precedence of undefined functions), parser Xor + chained comparisons, gcdex zero, euler rewrite at 0, Mul hermitian, Mod complex crash, matrix conjugate/Q.hermitian handlers, noncommutative linear solving, match/replace with bound symbols, floor/ceiling imaginary integers, Pow is_imaginary, zeta Laurent series, numeric floordiv by zero raises.

Could not identify (left alone): objective "common/failing assumptions" (core test_assumptions), partition-function change, exact Float/0 test.

**Why:** a later session may be asked to continue; /tmp/work (notes, baseline junit results, runner script) may not survive.
**How to apply:** re-derive status from a diff against a clean sympy 1.14.dev checkout before changing more; expected old-test failures after the work are test_args registry, test_basic/test_entity subs TypeError, old test_qs_2, lambdarepr multiple sums.
