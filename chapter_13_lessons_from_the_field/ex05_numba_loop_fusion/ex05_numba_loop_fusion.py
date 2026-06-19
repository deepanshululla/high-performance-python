"""ex05 — Numba's loop fusion erases the temporaries a NumPy array expression allocates.

Valentin Haenel's Numba chapter makes a point that surprises people: you do *not* need to
rewrite NumPy array expressions as explicit loops to make them fast under Numba — and you
shouldn't. A whole-array expression like

    a * b - 4.1 * a > 2.5 * b

forces NumPy to walk the arrays once per arithmetic operation, materialising a full-size
temporary array for each sub-result (`a*b`, `4.1*a`, their difference, `2.5*b`, the
comparison). Numba compiles the same expression and applies *loop fusion*: it collapses all
those per-operation loops into one pass that computes each output element from the inputs
directly, so no large temporary is ever allocated and the data is read once. The book
measures ~8x for this.

We compare four paths on identical inputs (anchored to be element-for-element equal):

  * numpy            — the array expression, with its chain of temporaries;
  * numba_auto       — the *same expression* under @njit (loop fusion does the work);
  * numba_manual     — an explicit @njit for-loop (what fusion effectively produces);
  * numpy_pure(loop) — the expression evaluated by a plain Python loop, for scale.

We also separate Numba's *cold* first call (which pays compilation) from the *warm* steady
state, the honest way to time a JIT.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root -> perf

import numpy as np  # noqa: E402
from numba import njit  # noqa: E402

from perf import time_s  # noqa: E402

N = 5_000_000


def _inputs(n=N, seed=0):
    rng = np.random.default_rng(seed)
    return rng.random(n), rng.random(n)


def expr_numpy(a, b):
    """NumPy: each sub-expression allocates a full-size temporary array."""
    return a * b - 4.1 * a > 2.5 * b


@njit
def expr_numba_auto(a, b):
    """Same array expression under @njit — Numba fuses the per-op loops into one pass."""
    return a * b - 4.1 * a > 2.5 * b


@njit
def expr_numba_manual(a, b):
    """The fused loop written by hand: one pass, one element at a time, no temporaries."""
    n = len(a)
    out = np.empty(n, dtype=np.bool_)
    for i in range(n):
        ai, bi = a[i], b[i]
        out[i] = ai * bi - 4.1 * ai > 2.5 * bi
    return out


def expr_python_loop(a, b):
    """Pure-Python loop over the arrays, for a sense of the unaccelerated baseline."""
    out = np.empty(len(a), dtype=np.bool_)
    for i in range(len(a)):
        ai, bi = a[i], b[i]
        out[i] = ai * bi - 4.1 * ai > 2.5 * bi
    return out


def measure(n=N, seed=0):
    a, b = _inputs(n, seed)
    ref = expr_numpy(a, b)

    # Cold calls compile (and validate correctness against numpy).
    import time
    t0 = time.perf_counter(); auto0 = expr_numba_auto(a, b); cold_auto = time.perf_counter() - t0
    t0 = time.perf_counter(); man0 = expr_numba_manual(a, b); cold_manual = time.perf_counter() - t0
    assert np.array_equal(ref, auto0) and np.array_equal(ref, man0), "numba diverged from numpy!"

    t_np = time_s(lambda: expr_numpy(a, b), number=1, repeat=5)
    t_auto = time_s(lambda: expr_numba_auto(a, b), number=1, repeat=5)
    t_manual = time_s(lambda: expr_numba_manual(a, b), number=1, repeat=5)
    # The pure-Python loop is ~100x slower; smaller slice, scaled to a per-element rate.
    small = n // 10
    pa, pb = a[:small], b[:small]
    assert np.array_equal(expr_python_loop(pa, pb), expr_numpy(pa, pb))
    t_py = time_s(lambda: expr_python_loop(pa, pb), number=1, repeat=2) * (n / small)
    return {
        "n": n,
        "numpy": t_np, "numba_auto": t_auto, "numba_manual": t_manual, "python_loop": t_py,
        "cold_auto": cold_auto, "cold_manual": cold_manual,
        "fusion_speedup": t_np / t_auto,
    }


def main():
    m = measure()
    print(f"evaluating  a*b - 4.1*a > 2.5*b  over {m['n']:,} floats:\n")
    for name in ("python_loop", "numpy", "numba_auto", "numba_manual"):
        print(f"  {name:14}: {m[name]*1e3:9.3f} ms")
    print(f"\n  loop fusion (numpy -> numba): {m['fusion_speedup']:.1f}x")
    print(f"  numba cold compile: auto {m['cold_auto']*1e3:.0f} ms, "
          f"manual {m['cold_manual']*1e3:.0f} ms (one-time)")


if __name__ == "__main__":
    main()
