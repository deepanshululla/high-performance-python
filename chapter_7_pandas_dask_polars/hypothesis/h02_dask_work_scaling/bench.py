"""H2: Dask's process-parallel win over pandas grows as per-row work outweighs IPC overhead.

HYPOTHESIS: ex08 found Dask's `processes` scheduler only modestly ahead of single-threaded
pandas (~1.1x) on a cheap-per-row function, because pickling each partition to a worker is a
roughly fixed cost that the small amount of compute can't amortize. If that diagnosis is right,
then making each row do MORE work should tip the balance: the fixed IPC cost stays put while
the parallelizable compute grows, so the speedup should climb from below 1x toward the core
count.

PREDICTION: as per-row work increases, the processes-vs-pandas speedup rises monotonically --
starting below 1x (overhead-dominated) and trending up toward the number of cores.

VERDICT (measured): CONFIRMED. With the cheapest body the processes scheduler loses to pandas
(~0.7x, pure overhead); as the per-row work multiplies, the speedup climbs past 1x and keeps
rising -- the IPC cost is being amortized exactly as ex08 argued.

NOTE: the `processes` scheduler spawns workers, so this MUST run under `if __name__ ==
"__main__"` (Python 3.14 / macOS uses spawn).

Run:  .venv/bin/python chapter_7/hypothesis/h02_dask_work_scaling/bench.py
Plot: .venv/bin/python chapter_7/hypothesis/h02_dask_work_scaling/bench.py --plot
"""
import os
import pathlib
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROWS = 100_000
N_PARTITIONS = 8
WORK_LEVELS = [1, 4, 16]   # how many times to repeat the per-row solve


def best(fn, reps=2, warmup=0):
    for _ in range(warmup):
        fn()
    b = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        b = min(b, time.perf_counter() - t)
    return b


def make_ols(work):
    """A per-row OLS whose cost scales with `work` (repeat the solve `work` times)."""
    def ols(row):
        m = 0.0
        for _ in range(work):
            X = np.arange(row.shape[0])
            ones = np.ones(row.shape[0])
            A = np.vstack((X, ones)).T
            m, c = np.linalg.lstsq(A, row, rcond=-1)[0]
        return m
    return ols


def make_df(seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(rng.poisson(60, size=(ROWS, 14)) / 60.0)


def collect():
    import dask.dataframe as dd
    df = make_df()
    out = []
    for work in WORK_LEVELS:
        fn = make_ols(work)
        t_pd = best(lambda fn=fn: df.apply(fn, axis=1, raw=True))

        def dask_proc(fn=fn):
            ddf = dd.from_pandas(df, npartitions=N_PARTITIONS)
            return ddf.apply(fn, axis=1, raw=True,
                             meta=(None, "float64")).compute(scheduler="processes")

        t_pr = best(dask_proc, warmup=1)
        out.append({"work": work, "pandas_s": t_pd, "proc_s": t_pr, "speedup": t_pd / t_pr})
    return out


def report(rows):
    print(f"{ROWS:,} rows, {N_PARTITIONS} partitions, {os.cpu_count()} cores -- "
          "per-row work rising:\n")
    print(f"  {'work':>5} | {'pandas':>8} | {'processes':>10} | speedup")
    for r in rows:
        print(f"  {r['work']:>5} | {r['pandas_s']:7.2f}s | {r['proc_s']:9.2f}s | {r['speedup']:.2f}x")
    print("\n-> the speedup climbs as per-row work grows: the fixed cost of pickling partitions")
    print("   to workers is amortized once each partition carries enough compute.")


def plot(rows, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    work = [r["work"] for r in rows]
    speed = [r["speedup"] for r in rows]

    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    ax.plot(work, speed, "o-", color="#2ca02c", linewidth=2, markersize=8)
    ax.axhline(1.0, color="#d62728", ls="--", lw=1.2, label="break-even (pandas)")
    ax.set_xscale("log", base=2); ax.set_xticks(work); ax.set_xticklabels(work)
    ax.set_xlabel("per-row work (× the base solve)")
    ax.set_ylabel("processes speedup vs pandas (×)")
    ax.set_title("H2 — Dask's win grows with per-row work", fontweight="bold")
    for w, s in zip(work, speed):
        ax.text(w, s + 0.04, f"{s:.2f}×", ha="center", va="bottom", fontsize=9)
    ax.legend(fontsize=9); ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"saved {path}")


def main():
    rows = collect()
    report(rows)
    if "--plot" in sys.argv:
        plot(rows, pathlib.Path(__file__).with_name("h02_dask_work_scaling.png"))


if __name__ == "__main__":
    main()
