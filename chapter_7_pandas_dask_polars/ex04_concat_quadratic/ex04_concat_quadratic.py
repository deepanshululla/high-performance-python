"""Chapter 7 - Exercise 4: building from a list vs iterative concat (Example 7-11, Figure 7-3).

Task: collect per-row results two ways -- append to a Python list and build one Series at
the end, versus `pd.concat` the running Series on every iteration -- and also measure how
the per-chunk cost of the concat approach grows as the Series gets longer.

Takeaway: a Series is backed by a contiguous array that can't grow in place, so each
`concat` allocates a fresh array one element longer and copies everything across.
Copying N elements on iteration N, summed over the run, is O(N^2) -- so each concat is
slower than the last. A Python list's append is amortized O(1), so accumulate there and
materialize the Series exactly once.

Run: .venv/bin/python chapter_7/ex04_concat_quadratic/ex04_concat_quadratic.py
"""
import pathlib
import sys
import time
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

warnings.filterwarnings("ignore")

ROWS = 8_000        # headline list-vs-concat: real OLS per row, kept bench-friendly
CHUNK_ROWS = 60_000  # growth curve: isolated pure concat, large enough for O(N^2) to show


def gen_df(n_rows=ROWS, n_days=14, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(rng.poisson(60, size=(n_rows, n_days)) / 60.0)


def ols_lstsq_raw(row):
    X = np.arange(row.shape[0])
    ones = np.ones(row.shape[0])
    A = np.vstack((X, ones)).T
    m, c = np.linalg.lstsq(A, row, rcond=-1)[0]
    return m


def via_list(df):
    """Append to a list (amortized O(1)), build the Series once at the end."""
    ms = [ols_lstsq_raw(df.iloc[i].to_numpy()) for i in range(df.shape[0])]
    return pd.Series(ms)


def via_concat(df):
    """Concatenate a new one-element Series every iteration -- the O(N^2) trap."""
    results = None
    for i in range(df.shape[0]):
        m = ols_lstsq_raw(df.iloc[i].to_numpy())
        s = pd.Series([m])
        results = s if results is None else pd.concat((results, s))
    return results


def concat_chunk_times(n=CHUNK_ROWS, chunks=10, seed=0):
    """Time each successive 10% block of *pure* concatenation to expose the growth (Figure 7-3).

    Values are precomputed so the only work timed is the concat copy itself -- otherwise the
    per-row OLS/iloc overhead is a large constant that hides the O(N^2) term at small N.
    """
    ms = np.random.default_rng(seed).random(n)
    bounds = [round(n * k / chunks) for k in range(chunks + 1)]
    times, results = [], None
    for lo, hi in zip(bounds, bounds[1:]):
        t = time.perf_counter()
        for i in range(lo, hi):
            s = pd.Series([ms[i]])
            results = s if results is None else pd.concat((results, s))
        times.append(time.perf_counter() - t)
    return times


def _best(fn, reps=2):
    b = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        b = min(b, time.perf_counter() - t)
    return b


def main():
    df = gen_df()

    assert np.allclose(via_list(df).to_numpy(), via_concat(df).to_numpy())
    print(f"Both approaches agree on the {df.shape[0]:,} results.\n")

    t_list = _best(lambda: via_list(df))
    t_concat = _best(lambda: via_concat(df))
    print(f"Accumulating {df.shape[0]:,} per-row results:")
    print(f"  list + one Series : {t_list:6.3f} s   (1.0x)")
    print(f"  iterative concat  : {t_concat:6.3f} s   ({t_concat / t_list:.1f}x slower)")

    chunks = concat_chunk_times()
    print(f"\nPer-10%-chunk pure-concat cost ({CHUNK_ROWS:,} single-element appends, each block "
          f"{CHUNK_ROWS // 10:,}):")
    for k, c in enumerate(chunks, 1):
        bar = "#" * round(c / max(chunks) * 40)
        print(f"  {k * 10:3d}% : {c * 1e3:6.1f} ms  {bar}")
    print(f"  -> the last chunk is {chunks[-1] / chunks[0]:.1f}x the first: each concat copies the")
    print("     whole growing Series, so cost rises with length -- the O(N^2) signature.")


if __name__ == "__main__":
    main()
