"""ex07 — SciPy sparse matrices: when storing only the non-zeros pays off.

A sparse matrix is one whose entries are mostly zero. SciPy's CSR (Compressed Sparse
Row) format stores only the non-zero values plus the indices needed to locate them, and
treats everything else as an implicit zero. That buys two things at low density: far less
memory (you don't store the zeros) and far less work (multiplication only touches the
non-zeros). But the indices are themselves overhead — CSR keeps a value *and* a column
index for each non-zero — so as the matrix fills up, that bookkeeping eventually costs
more than just storing every value densely, and dense NumPy (backed by cache-friendly,
SIMD-vectorised BLAS) pulls ahead.

We hold the matrix size fixed at 2048x2048 and sweep the density from 0.1% up toward 50%,
measuring at each point both the time to square the matrix (sparse CSR vs dense NumPy) and
the memory each representation occupies. This reproduces the book's Figures 12-5 (speed)
and 12-6 (footprint), including the crossover where dense overtakes sparse.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root -> perf
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir

import numpy as np  # noqa: E402
from scipy import sparse  # noqa: E402

from perf import time_s  # noqa: E402

N = 2048
DENSITIES = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.33, 0.5]
MIB = 1024 * 1024


def make_sparse(n=N, density=0.01, seed=0):
    rng = np.random.default_rng(seed)
    return sparse.random(n, n, density=density, format="csr", random_state=rng)


def sparse_bytes(A):
    """CSR footprint: the non-zero values plus their column indices plus row pointers."""
    return A.data.nbytes + A.indices.nbytes + A.indptr.nbytes


def dense_bytes(n=N):
    return n * n * 8        # float64, every cell stored


def measure(n=N, densities=DENSITIES):
    """For each density: sparse/dense multiply time (s) and memory (MiB)."""
    rows = []
    for d in densities:
        A = make_sparse(n, d)
        Ad = A.toarray()
        # correctness anchor: the two products must agree
        if d == densities[0]:
            assert np.allclose((A @ A).toarray(), Ad @ Ad), "sparse/dense product mismatch!"
        t_sparse = time_s(lambda: A @ A, number=1, repeat=3)
        t_dense = time_s(lambda: Ad @ Ad, number=1, repeat=3)
        rows.append({
            "density": d,
            "t_sparse": t_sparse, "t_dense": t_dense,
            "mem_sparse_mib": sparse_bytes(A) / MIB,
            "mem_dense_mib": dense_bytes(n) / MIB,
        })
    return rows


def main():
    rows = measure()
    print(f"{N}x{N} matrix, squared (A @ A); dense is always "
          f"{dense_bytes() / MIB:.1f} MiB:\n")
    print(f"  {'density':>8} {'sparse t':>10} {'dense t':>10} {'speedup':>9} "
          f"{'sparse MiB':>11}")
    for r in rows:
        sp = r["t_dense"] / r["t_sparse"]
        flag = "sparse wins" if sp > 1 else "dense wins"
        print(f"  {r['density']:8.3f} {r['t_sparse']*1e3:9.2f}m {r['t_dense']*1e3:9.2f}m "
              f"{sp:8.2f}x {r['mem_sparse_mib']:10.1f}  {flag}")
    # find the speed crossover
    cross = next((r["density"] for r in rows if r["t_sparse"] >= r["t_dense"]), None)
    print(f"\n  speed crossover near density {cross}: below it sparse multiply wins, "
          f"above it dense BLAS wins.")
    print(f"  memory: sparse beats dense's {dense_bytes()/MIB:.1f} MiB until the "
          f"non-zeros (value+index each) outweigh storing every cell.")


if __name__ == "__main__":
    main()
