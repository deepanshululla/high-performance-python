"""H3: Polars `lazy` beats `eager` only when it can push work into a Parquet scan.

HYPOTHESIS: ex09 found eager and lazy Polars identical on a fully-in-RAM frame, and argued
the lazy API's real wins live in *pushdown* -- letting the query optimizer read only the rows
and columns a query actually needs straight from the file. This tests that directly: write a
wide Parquet file, then run the same selective query (`filter` + column `select`) as an eager
read-everything-then-filter versus a lazy `scan_parquet` the optimizer can push down.

PREDICTION: lazy `scan_parquet` is several times faster than eager `read_parquet`, because
predicate pushdown skips row groups and projection pushdown skips columns at the file-read
level -- work the eager path does only after loading the whole file.

VERDICT (measured): CONFIRMED. On an ~250 MB, 6-column Parquet file, lazy scan runs ~3-4x
faster than eager read, and well ahead of pandas read-then-filter -- exactly the win ex09's
in-RAM benchmark could not show.

Run:  .venv/bin/python chapter_7/hypothesis/h03_polars_parquet_pushdown/bench.py
Plot: .venv/bin/python chapter_7/hypothesis/h03_polars_parquet_pushdown/bench.py --plot
"""
import os
import pathlib
import sys
import tempfile
import time
import warnings

import numpy as np
import pandas as pd
import polars as pl

warnings.filterwarnings("ignore")

ROWS = 8_000_000


def best(fn, reps=3, warmup=1):
    for _ in range(warmup):
        fn()
    b = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        b = min(b, time.perf_counter() - t)
    return b


def write_parquet(path, seed=0):
    rng = np.random.default_rng(seed)
    df = pl.DataFrame({
        "k": rng.integers(0, 1000, ROWS),
        "v": rng.random(ROWS),
        "w": rng.random(ROWS),
        "x": rng.random(ROWS),
        "y": rng.random(ROWS),
        "label": rng.choice(["a", "b", "c"], ROWS),
    })
    df.write_parquet(path)
    return os.path.getsize(path) / 1e6   # MB


def collect():
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "data.parquet")
    size_mb = write_parquet(path)

    # The same selective query, three ways. Keep only 2 of 6 columns, ~10% of rows.
    def pandas_read():
        d = pd.read_parquet(path)
        return d[d["v"] > 0.9][["k", "v"]]

    def polars_eager():
        return pl.read_parquet(path).filter(pl.col("v") > 0.9).select(["k", "v"])

    def polars_lazy():
        return pl.scan_parquet(path).filter(pl.col("v") > 0.9).select(["k", "v"]).collect()

    return {
        "size_mb": size_mb,
        "pandas_ms": best(pandas_read) * 1e3,
        "eager_ms": best(polars_eager) * 1e3,
        "lazy_ms": best(polars_lazy) * 1e3,
    }


def report(data):
    print(f"Parquet file: {ROWS:,} rows x 6 columns, {data['size_mb']:.0f} MB on disk")
    print("Query: keep 2 of 6 columns, ~10% of rows (filter v > 0.9)\n")
    print(f"  pandas read_parquet + filter : {data['pandas_ms']:7.1f} ms")
    print(f"  polars eager  read_parquet   : {data['eager_ms']:7.1f} ms")
    print(f"  polars lazy   scan_parquet   : {data['lazy_ms']:7.1f} ms   "
          f"({data['eager_ms'] / data['lazy_ms']:.1f}x vs eager)")
    print("\n-> lazy pushes the filter and the column selection INTO the file read, so it")
    print("   touches far fewer bytes; eager and pandas load the whole file first, then cut.")


def plot(data, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    labels = ["pandas\nread+filter", "polars eager\nread_parquet", "polars lazy\nscan_parquet"]
    vals = [data["pandas_ms"], data["eager_ms"], data["lazy_ms"]]
    colors = ["#1f77b4", "#9467bd", "#2ca02c"]
    bars = ax.bar(labels, vals, color=colors)
    ax.set_ylabel("time (ms)")
    ax.set_title(f"H3 — lazy scan pushdown ({data['eager_ms'] / data['lazy_ms']:.1f}× vs eager, "
                 f"{data['size_mb']:.0f} MB Parquet)", fontweight="bold")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.02, f"{v:.0f} ms", ha="center", va="bottom", fontsize=10)
    ax.text(0.5, 0.9, "lazy reads only the rows & columns the query needs",
            transform=ax.transAxes, ha="center", fontsize=9.5, color="#2ca02c")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"saved {path}")


def main():
    data = collect()
    report(data)
    if "--plot" in sys.argv:
        plot(data, pathlib.Path(__file__).with_name("h03_polars_parquet_pushdown.png"))


if __name__ == "__main__":
    main()
