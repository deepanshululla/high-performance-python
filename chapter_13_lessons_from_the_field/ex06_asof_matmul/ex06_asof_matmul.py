"""ex06 — Mikhail Timonin's PSP': a Numba loop avoids NumPy's T x N x N memory blowup.

In quant finance you often hold a matrix of portfolio positions P with shape (T, N) — N
assets across T timestamps — and a coarser risk matrix S with shape (t, N, N), where t << T
(risk is recomputed daily, positions move every tick). For each timestamp you want the
portfolio risk  p . S . p , using the *as-of* risk matrix (the most recent daily S at or
before that timestamp). Timonin's warning: "Doing it in a naive way with NumPy will first
blow up S to T x N x N, and you might well be out of memory by then." A Numba loop, by
contrast, "can efficiently hop through timestamps in T, picking up the appropriate positions
(exact) and risk (as-of) slices, and do the job in no time" — with an O(N^2) working set.

Three paths, anchored to the same per-timestamp risk vector:

  * numpy_broadcast — gather S up to a full (T, N, N) array, then one einsum. Fast arithmetic,
                      but it allocates a temporary of T*N*N floats.
  * python_loop     — hop through T in Python doing p @ S_asof @ p. Tiny memory, slow.
  * numba_asof      — the same hop compiled with @njit. Tiny memory *and* fast.

We report both wall-clock time and peak resident memory (measured in a fresh process each).
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root -> perf
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir -> _rss

import numpy as np  # noqa: E402
from numba import njit  # noqa: E402

from _rss import peak_rss_mib  # noqa: E402
from perf import time_s  # noqa: E402

T = 100_000     # timestamps (ticks)
N = 20          # assets
T_RISK = 250    # distinct daily risk matrices (t << T)


def _inputs(seed=0):
    rng = np.random.default_rng(seed)
    P = rng.standard_normal((T, N))
    # Symmetric positive-ish risk matrices (covariance-like): A @ A.T.
    A = rng.standard_normal((T_RISK, N, N))
    S = A @ A.transpose(0, 2, 1)
    # as-of map: every tick points at the most recent daily risk matrix.
    asof = np.minimum(np.arange(T) * T_RISK // T, T_RISK - 1)
    return P, S, asof


def risk_numpy_broadcast(P, S, asof):
    """Gather S to (T, N, N) — the blowup — then one einsum for p . S . p per timestamp."""
    S_full = S[asof]                                   # shape (T, N, N): the big temporary
    return np.einsum("ti,tij,tj->t", P, S_full, P)


def risk_python_loop(P, S, asof):
    """Hop through T in Python; only an N x N slice is ever touched."""
    out = np.empty(T)
    for k in range(T):
        p = P[k]
        out[k] = p @ S[asof[k]] @ p
    return out


@njit
def risk_numba_asof(P, S, asof):
    """The same hop, compiled: O(N^2) work per timestamp, O(N^2) working set, no big temp."""
    T_, N_ = P.shape
    out = np.empty(T_)
    for k in range(T_):
        si = asof[k]
        acc = 0.0
        for i in range(N_):
            pi = P[k, i]
            for j in range(N_):
                acc += pi * S[si, i, j] * P[k, j]
        out[k] = acc
    return out


# Top-level wrappers so _rss's spawned child can pickle them by name.
def _full_numpy():
    return risk_numpy_broadcast(*_inputs())


def _full_python():
    return risk_python_loop(*_inputs())


def _full_numba():
    P, S, asof = _inputs()
    return risk_numba_asof(P, S, asof)


def measure():
    P, S, asof = _inputs()
    ref = risk_numpy_broadcast(P, S, asof)
    warm = risk_numba_asof(P, S, asof)                 # cold compile + correctness
    assert np.allclose(ref, risk_python_loop(P, S, asof)), "python loop diverged!"
    assert np.allclose(ref, warm), "numba diverged!"

    t_np = time_s(lambda: risk_numpy_broadcast(P, S, asof), number=1, repeat=3)
    t_py = time_s(lambda: risk_python_loop(P, S, asof), number=1, repeat=2)
    t_nb = time_s(lambda: risk_numba_asof(P, S, asof), number=1, repeat=5)

    mem_np = peak_rss_mib(_full_numpy)
    mem_py = peak_rss_mib(_full_python)
    mem_nb = peak_rss_mib(_full_numba)
    return {
        "T": T, "N": N, "t_risk": T_RISK,
        "broadcast_mib": T * N * N * 8 / 1024**2,       # the (T,N,N) temporary, analytically
        "numpy": {"s": t_np, "rss_mib": mem_np},
        "python": {"s": t_py, "rss_mib": mem_py},
        "numba": {"s": t_nb, "rss_mib": mem_nb},
    }


def main():
    m = measure()
    print(f"PSP' over T={m['T']:,} ticks, N={m['N']} assets, {m['t_risk']} daily risk matrices")
    print(f"(the (T,N,N) gather alone is {m['broadcast_mib']:.0f} MiB):\n")
    for name in ("numpy", "python", "numba"):
        d = m[name]
        print(f"  {name:8}: {d['s']*1e3:8.2f} ms   peak RSS {d['rss_mib']:7.1f} MiB")
    print(f"\n  numba vs numpy: {m['numpy']['s']/m['numba']['s']:.1f}x faster, "
          f"{m['numpy']['rss_mib']/max(m['numba']['rss_mib'],1):.0f}x less memory")


if __name__ == "__main__":
    main()
