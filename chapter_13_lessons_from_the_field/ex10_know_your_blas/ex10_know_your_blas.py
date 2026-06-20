"""ex10 — know your BLAS: numpy's matmul is vendor-tuned assembly, not a loop.

Radim Řehůřek's last optimisation in making Python word2vec beat C was "know your BLAS":
"numpy internally wraps Basic Linear Algebra Subprograms (BLAS)... optimized directly by
processor vendors in assembly, Fortran, or C... Expressing word2vec training as BLAS
operations resulted in another four times speedup, topping the performance of C word2vec."
The lesson is that the fast path for numerical work isn't "write a loop, maybe compile it" —
it's "phrase it as a BLAS call (dot, gemm, axpy) and let numpy hand it to code that has been
tuned for this exact CPU for decades."

We demonstrate with the canonical BLAS routine, matrix multiply (gemm), on identical inputs:

  * python_loop — the textbook triple `for` loop. Correct, and catastrophically slow.
  * numba_loop  — the same triple loop compiled with @njit. Compilation removes the
                  interpreter overhead, but it's still a naive loop with no cache blocking.
  * numpy_blas  — `A @ B`, which dispatches to the platform BLAS.

We report GFLOP/s for each (matmul is 2*N^3 floating-point ops), and then a separate
large-matrix run to show what fraction of the machine the BLAS path actually reaches.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root -> perf

import numpy as np  # noqa: E402
from numba import njit  # noqa: E402

from perf import time_s  # noqa: E402

N = 128            # small enough that the pure-Python triple loop finishes
N_BIG = 2000       # large enough to show BLAS near its steady-state throughput


def _inputs(n, seed=0):
    rng = np.random.default_rng(seed)
    return rng.standard_normal((n, n)), rng.standard_normal((n, n))


def matmul_python(A, B):
    """Textbook triple loop, pure Python."""
    n = A.shape[0]
    C = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            s = 0.0
            for k in range(n):
                s += A[i, k] * B[k, j]
            C[i, j] = s
    return C


@njit
def matmul_numba(A, B):
    """The identical triple loop, compiled — no interpreter overhead, but still naive."""
    n = A.shape[0]
    C = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            s = 0.0
            for k in range(n):
                s += A[i, k] * B[k, j]
            C[i, j] = s
    return C


def matmul_blas(A, B):
    """A @ B — dispatches to the platform BLAS gemm."""
    return A @ B


def _gflops(n, seconds):
    return (2 * n ** 3) / seconds / 1e9


def measure():
    A, B = _inputs(N)
    ref = matmul_blas(A, B)
    warm = matmul_numba(A, B)                     # cold compile + correctness
    assert np.allclose(ref, matmul_python(A, B)) and np.allclose(ref, warm), "matmul diverged!"

    t_py = time_s(lambda: matmul_python(A, B), number=1, repeat=1)
    t_nb = time_s(lambda: matmul_numba(A, B), number=1, repeat=5)
    t_np = time_s(lambda: matmul_blas(A, B), number=1, repeat=10)

    # Big-matrix BLAS run: what throughput does the vendor routine actually reach?
    Ab, Bb = _inputs(N_BIG)
    matmul_blas(Ab, Bb)                           # warm any first-call setup
    t_big = time_s(lambda: matmul_blas(Ab, Bb), number=1, repeat=3)

    return {
        "n": N, "n_big": N_BIG,
        "python": {"s": t_py, "gflops": _gflops(N, t_py)},
        "numba": {"s": t_nb, "gflops": _gflops(N, t_nb)},
        "numpy": {"s": t_np, "gflops": _gflops(N, t_np)},
        "blas_big_gflops": _gflops(N_BIG, t_big),
        "py_vs_blas": t_py / t_np,
        "numba_vs_blas": t_nb / t_np,
    }


def main():
    m = measure()
    print(f"matrix multiply, {m['n']}x{m['n']} (2*N^3 = {2*m['n']**3/1e6:.1f}M flops):\n")
    for name in ("python", "numba", "numpy"):
        d = m[name]
        print(f"  {name:7}: {d['s']*1e3:9.2f} ms   {d['gflops']:8.2f} GFLOP/s")
    print(f"\n  numpy/BLAS is {m['py_vs_blas']:,.0f}x faster than the Python loop, "
          f"{m['numba_vs_blas']:.0f}x faster than the compiled loop")
    print(f"  on a {m['n_big']}x{m['n_big']} multiply, BLAS sustains "
          f"{m['blas_big_gflops']:.0f} GFLOP/s")


if __name__ == "__main__":
    main()
