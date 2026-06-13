"""Chapter 7 - Exercise 8: parallelizing apply with Dask (Examples 7-13, 7-14).

Task: run the same `raw=True` row-wise OLS over a large DataFrame three ways -- plain
single-threaded pandas, Dask with the default `threads` scheduler, and Dask with the
`processes` scheduler -- and compare.

Takeaway: pandas' row `apply` is GIL-bound, so the default thread scheduler gives NO
speedup (often a small slowdown from coordination overhead). To use multiple cores you
must switch to `processes`, which sidesteps the GIL at the cost of pickling partitions to
worker processes. On small data that IPC overhead can erase the win -- the gain only
appears once each partition carries enough CPU work to amortize it.

NOTE: the `processes` scheduler spawns workers, so this MUST run under `if __name__ ==
"__main__"` (Python 3.14 on macOS uses spawn, which re-imports the module in children).

Run: .venv/bin/python chapter_7/ex08_dask_parallel_apply/ex08_dask_parallel_apply.py
"""
import os
import pathlib
import sys
import time
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

warnings.filterwarnings("ignore")

BASE_ROWS = 20_000
MULTIPLIER = 40          # fake a larger frame, as the book does (Example 7-13)
N_PARTITIONS = 8


def gen_big(seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(rng.poisson(60, size=(BASE_ROWS, 14)) / 60.0)
    return pd.concat([df] * MULTIPLIER, ignore_index=True)


def ols_lstsq_raw(row):
    X = np.arange(row.shape[0])
    ones = np.ones(row.shape[0])
    A = np.vstack((X, ones)).T
    m, c = np.linalg.lstsq(A, row, rcond=-1)[0]
    return m


def run_pandas(df):
    return df.apply(ols_lstsq_raw, axis=1, raw=True)


def run_dask(df, scheduler, npartitions=N_PARTITIONS):
    import dask.dataframe as dd
    ddf = dd.from_pandas(df, npartitions=npartitions)
    return ddf.apply(ols_lstsq_raw, axis=1, raw=True,
                     meta=(None, "float64")).compute(scheduler=scheduler)


def _best(fn, reps=2, warmup=0):
    for _ in range(warmup):
        fn()
    b = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        b = min(b, time.perf_counter() - t)
    return b


def main():
    df = gen_big()
    print(f"DataFrame: {len(df):,} rows x {df.shape[1]} cols on a {os.cpu_count()}-core machine, "
          f"{N_PARTITIONS} Dask partitions.\n")

    t_pd = _best(lambda: run_pandas(df))
    t_th = _best(lambda: run_dask(df, "threads"), warmup=1)
    t_pr = _best(lambda: run_dask(df, "processes"), warmup=1)

    print(f"Row-wise OLS over {len(df):,} rows:")
    print(f"  pandas (single thread) : {t_pd:6.2f} s   (1.00x)")
    print(f"  dask  threads          : {t_th:6.2f} s   ({t_pd / t_th:.2f}x)  <- GIL-bound, no win")
    print(f"  dask  processes        : {t_pr:6.2f} s   ({t_pd / t_pr:.2f}x)  <- real cores")
    print("  -> threads can't parallelize GIL-bound pandas; processes can, once the")
    print("     per-partition work outweighs the cost of pickling data to workers.")


if __name__ == "__main__":
    main()
