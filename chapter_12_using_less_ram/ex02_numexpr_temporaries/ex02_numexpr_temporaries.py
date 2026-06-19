"""ex02 — the hidden RAM cost of NumPy temporaries, and how NumExpr erases it.

A vectorised expression like the cross-entropy / log-loss formula

    -(yt * log(yp) + (1 - yt) * log(1 - yp))

looks like one line, but NumPy evaluates it left-to-right, materialising a brand-new
full-size array for every sub-expression: `log(yp)`, `1 - yt`, `1 - yp`, `log(1-yp)`,
two products, a sum, a negation. With million-element inputs those temporaries dwarf
the inputs themselves, and the peak can be several times the size of the result.

NumExpr takes the same expression *as a string*, compiles it, and walks the arrays in
small cache-sized chunks, so only one chunk's worth of intermediate values is ever
live. The result is identical, but it needs essentially no extra RAM and runs several
times faster (it also threads across cores). We measure both the peak resident memory
of the whole routine and the wall-clock of just the evaluation step.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root -> perf
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir -> _mem

import numexpr  # noqa: E402
import numpy as np  # noqa: E402

from _mem import peak_rss_mib  # noqa: E402
from perf import time_s  # noqa: E402

# 50M elements: each float64 array is ~400 MB, enough that the temporaries dominate.
# (The book uses 200M; we scale down 4x so the suite runs in seconds — the *ratio* of
# the two peaks, not the absolute gigabytes, is the lesson.)
N = 50_000_000
EXPR = "-(yt * log(yp) + ((1 - yt) * (log(1 - yp))))"


def _inputs(n=N):
    rng = np.random.default_rng(0)
    yp = rng.uniform(low=1e-7, high=1.0, size=n)
    yt = np.ones(n)
    return yp, yt


def crossentropy_numpy(yp, yt):
    """Direct NumPy: every sub-expression allocates a full-size temporary array."""
    return -(yt * np.log(yp) + ((1 - yt) * (np.log(1 - yp))))


def crossentropy_numexpr(yp, yt):
    """NumExpr: chunked evaluation, no large temporaries, multi-threaded."""
    return numexpr.evaluate(EXPR, local_dict={"yp": yp, "yt": yt})


def _full_numpy(n=N):
    yp, yt = _inputs(n)
    return crossentropy_numpy(yp, yt)


def _full_numexpr(n=N):
    yp, yt = _inputs(n)
    return crossentropy_numexpr(yp, yt)


def measure(n=N):
    """Return peak RSS (MiB) and eval time (s) for the numpy and numexpr paths."""
    peak_np = peak_rss_mib(_full_numpy, n)
    peak_ne = peak_rss_mib(_full_numexpr, n)
    yp, yt = _inputs(n)
    # correctness anchor: both paths must agree to floating-point tolerance
    a = crossentropy_numpy(yp, yt)
    b = crossentropy_numexpr(yp, yt)
    assert np.allclose(a, b), "numexpr result diverged from numpy!"
    t_np = time_s(lambda: crossentropy_numpy(yp, yt), number=1, repeat=3)
    t_ne = time_s(lambda: crossentropy_numexpr(yp, yt), number=1, repeat=3)
    return {
        "numpy": {"peak_mib": peak_np, "time_s": t_np},
        "numexpr": {"peak_mib": peak_ne, "time_s": t_ne},
    }


def main():
    m = measure()
    print(f"cross-entropy over {N:,} float64 elements (one input array ≈ "
          f"{N * 8 / 1024**2:.0f} MiB):\n")
    for name in ("numpy", "numexpr"):
        d = m[name]
        print(f"  {name:8}: peak RSS {d['peak_mib']:7.0f} MiB   "
              f"eval {d['time_s']:.3f}s")
    print(f"\n  peak RAM saved: {m['numpy']['peak_mib'] - m['numexpr']['peak_mib']:.0f} MiB"
          f"   speedup: {m['numpy']['time_s'] / m['numexpr']['time_s']:.1f}x")


if __name__ == "__main__":
    main()
