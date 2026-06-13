"""Chapter 7 - Exercise 3: compiling the row function with Numba (Examples 7-10..7-14).

Task: take the `raw=True` apply from ex02 and progressively compile it -- plain Python,
a precompiled `numba.jit` function, the built-in `engine="numba"` fast path, and finally
`engine="numba"` with `parallel=True` to spread rows across cores.

Takeaway: native compilation deletes the CPython bytecode-dispatch overhead on the tight
numeric body, and `parallel=True` farms the embarrassingly-parallel rows across cores
free of the GIL -- compounding to a large speedup. The entry ticket is NumPy storage:
Numba cannot compile a pandas Series or a PyArrow array, which is exactly why ex02's
`raw=True` (bare NumPy array) was the prerequisite.

Run: .venv/bin/python chapter_7/ex03_numba_compile/ex03_numba_compile.py
"""
import pathlib
import sys
import time
import warnings

import numpy as np
import pandas as pd
from numba import jit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

warnings.filterwarnings("ignore")

GRID_ROWS = 20_000


def gen_df(n_rows=GRID_ROWS, n_days=14, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(rng.poisson(60, size=(n_rows, n_days)) / 60.0)


def ols_lstsq_raw(row):
    """Bare-NumPy OLS slope -- the only form Numba can compile."""
    X = np.arange(row.shape[0])
    ones = np.ones(row.shape[0])
    A = np.vstack((X, ones)).T
    m, c = np.linalg.lstsq(A, row, rcond=-1)[0]
    return m


# A precompiled Numba variant (compiled once, on first call).
ols_numba = jit(ols_lstsq_raw, nopython=True)


def run_plain(df):
    return df.apply(ols_lstsq_raw, axis=1, raw=True)


def run_jit(df):
    return df.apply(ols_numba, axis=1, raw=True)


def run_engine(df):
    return df.apply(ols_lstsq_raw, axis=1, raw=True, engine="numba")


def run_engine_parallel(df):
    return df.apply(ols_lstsq_raw, axis=1, raw=True,
                    engine="numba", engine_kwargs={"parallel": True})


def _best(fn, reps=3, warmup=1):
    for _ in range(warmup):    # first call pays Numba's one-off compile cost
        fn()
    b = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        b = min(b, time.perf_counter() - t)
    return b


def main():
    df = gen_df()

    methods = [
        ("apply raw (no compile) ", run_plain),
        ("jit precompiled        ", run_jit),
        ("engine='numba'         ", run_engine),
        ("engine='numba' parallel", run_engine_parallel),
    ]

    base = run_plain(df).to_numpy()
    for name, fn in methods:
        assert np.allclose(fn(df).to_numpy(), base), name
    print(f"All variants agree on the {df.shape[0]:,} slopes.\n")

    print(f"Row-wise OLS over {df.shape[0]:,} rows (times exclude one-off compile):")
    t0 = None
    for name, fn in methods:
        t = _best(lambda fn=fn: fn(df))
        if t0 is None:
            t0 = t
        print(f"  {name}: {t * 1e3:7.1f} ms   ({t0 / t:5.1f}x vs uncompiled)")
    print("  -> compilation kills interpreter overhead; parallel=True adds GIL-free cores.")
    print("     Both need NumPy storage -- Numba can't touch Series or PyArrow arrays.")


if __name__ == "__main__":
    main()
