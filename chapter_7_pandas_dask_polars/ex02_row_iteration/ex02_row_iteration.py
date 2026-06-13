"""Chapter 7 - Exercise 2: four ways to apply a function to every row (Table 7-1).

Task: run the same OLS slope calculation over every row of a DataFrame four ways --
`iloc` in a loop, `iterrows`, `apply(axis=1)`, and `apply(axis=1, raw=True)` -- and
time each.

Takeaway: the per-row *vehicle*, not the arithmetic, sets the speed. `iloc` and
`iterrows` build and dereference a fresh `Series` object for every row through extra
Python machinery; `apply` skips those intermediates; `raw=True` hands the function
the bare NumPy array and skips even `apply`'s internal Series. That bare-array form is
also the only one Numba/Cython can later compile (see ex03).

Run: .venv/bin/python chapter_7/ex02_row_iteration/ex02_row_iteration.py
"""
import pathlib
import sys
import time
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

warnings.filterwarnings("ignore")

GRID_ROWS = 20_000   # the book uses 100k; 20k keeps the slow iloc path bench-friendly


def gen_df(n_rows=GRID_ROWS, n_days=14, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(rng.poisson(60, size=(n_rows, n_days)) / 60.0)


def ols_lstsq(row):
    """Takes a pandas Series (row.values pulls the underlying array)."""
    X = np.arange(row.shape[0])
    ones = np.ones(row.shape[0])
    A = np.vstack((X, ones)).T
    m, c = np.linalg.lstsq(A, row.values, rcond=-1)[0]
    return m


def ols_lstsq_raw(row):
    """Takes a raw NumPy array directly -- no Series, so Numba/Cython can compile it."""
    X = np.arange(row.shape[0])
    ones = np.ones(row.shape[0])
    A = np.vstack((X, ones)).T
    m, c = np.linalg.lstsq(A, row, rcond=-1)[0]
    return m


def via_iloc(df):
    ms = []
    for i in range(df.shape[0]):
        ms.append(ols_lstsq(df.iloc[i]))     # fresh Series built on every dereference
    return pd.Series(ms)


def via_iterrows(df):
    ms = []
    for _, row in df.iterrows():             # still a fresh Series per row
        ms.append(ols_lstsq(row))
    return pd.Series(ms)


def via_apply(df):
    return df.apply(ols_lstsq, axis=1)       # no Python-level intermediate references


def via_apply_raw(df):
    return df.apply(ols_lstsq_raw, axis=1, raw=True)   # bare NumPy array, no Series


def _best(fn, reps=2):
    b = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        b = min(b, time.perf_counter() - t)
    return b


def main():
    df = gen_df()

    methods = [
        ("iloc      ", via_iloc),
        ("iterrows  ", via_iterrows),
        ("apply     ", via_apply),
        ("apply raw ", via_apply_raw),
    ]

    # Correctness: every method produces the same slopes.
    base = via_apply_raw(df).to_numpy()
    for name, fn in methods:
        assert np.allclose(fn(df).to_numpy(), base), name
    print(f"All four methods agree on the {df.shape[0]:,} slopes.\n")

    print(f"Row-wise OLS over {df.shape[0]:,} rows x {df.shape[1]} columns:")
    t_iloc = None
    for name, fn in methods:
        t = _best(lambda fn=fn: fn(df))
        if t_iloc is None:
            t_iloc = t
        print(f"  {name}: {t:6.3f} s   ({t_iloc / t:4.1f}x vs iloc)")
    print("  -> iloc/iterrows pay for a fresh Series per row; apply skips it;")
    print("     raw=True drops even apply's Series and unlocks Numba (ex03).")


if __name__ == "__main__":
    main()
