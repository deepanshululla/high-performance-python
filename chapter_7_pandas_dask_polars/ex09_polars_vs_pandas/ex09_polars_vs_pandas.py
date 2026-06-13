"""Chapter 7 - Exercise 9: Polars vs Pandas on a multi-step query (Polars section).

Task: run the same realistic pipeline -- filter rows, derive a column, group-by-aggregate,
sort, take the top 10 -- in pandas and in Polars (both eager and lazy), and compare.

Takeaway: Polars stores data only in Arrow, runs a built-in query optimizer, and
parallelizes across cores automatically -- so an equivalent set of operations typically
runs several times faster than pandas with no manual tuning. The lazy API (`.lazy()...
.collect()`) lets the optimizer see the whole plan at once; on an in-RAM frame where every
column is used it matches eager, but it is what unlocks predicate/projection pushdown when
scanning from Parquet, and the experimental streaming mode for larger-than-RAM data.

Run: .venv/bin/python chapter_7/ex09_polars_vs_pandas/ex09_polars_vs_pandas.py
"""
import pathlib
import sys
import time
import warnings

import numpy as np
import pandas as pd
import polars as pl

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

warnings.filterwarnings("ignore")

ROWS = 5_000_000


def gen_frames(n=ROWS, seed=0):
    rng = np.random.default_rng(seed)
    data = {"k": rng.integers(0, 1000, n), "v": rng.random(n), "w": rng.random(n)}
    return pd.DataFrame(data), pl.DataFrame(data)


def pandas_query(pdf):
    d = pdf[pdf["v"] > 0.5].copy()
    d["vw"] = d["v"] * d["w"]
    g = d.groupby("k").agg(mvw=("vw", "mean"), n=("vw", "size")).reset_index()
    return g.sort_values("mvw", ascending=False).head(10)


def _polars_plan(frame):
    return (frame.filter(pl.col("v") > 0.5)
            .with_columns((pl.col("v") * pl.col("w")).alias("vw"))
            .group_by("k").agg(pl.col("vw").mean().alias("mvw"), pl.len().alias("n"))
            .sort("mvw", descending=True).head(10))


def polars_eager(pldf):
    return _polars_plan(pldf)


def polars_lazy(pldf):
    return _polars_plan(pldf.lazy()).collect()


def _best(fn, reps=3, warmup=1):
    for _ in range(warmup):
        fn()
    b = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        b = min(b, time.perf_counter() - t)
    return b


def main():
    pdf, pldf = gen_frames()

    # Correctness: the top key by mean(vw) matches across engines.
    top_pd = int(pandas_query(pdf).iloc[0]["k"])
    top_pl = int(polars_lazy(pldf)["k"][0])
    assert top_pd == top_pl, (top_pd, top_pl)
    print(f"Both engines pick the same top key (k={top_pd}) on {ROWS:,} rows.\n")

    t_pd = _best(lambda: pandas_query(pdf))
    t_pe = _best(lambda: polars_eager(pldf))
    t_pl = _best(lambda: polars_lazy(pldf))

    print(f"filter -> derive -> groupby-agg -> sort -> head(10) over {ROWS:,} rows:")
    print(f"  pandas        : {t_pd * 1e3:6.1f} ms   (1.0x)")
    print(f"  polars eager  : {t_pe * 1e3:6.1f} ms   ({t_pd / t_pe:.1f}x)")
    print(f"  polars lazy   : {t_pl * 1e3:6.1f} ms   ({t_pd / t_pl:.1f}x)")
    print("  -> Arrow-only storage + a baked-in query optimizer + automatic multicore,")
    print("     with no manual tuning. Lazy unlocks pushdown when scanning from Parquet.")


if __name__ == "__main__":
    main()
