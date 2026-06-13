"""H1: converting a low-cardinality string key to `category` speeds up groupby AND cuts RAM.

HYPOTHESIS: The chapter's advice ("for large Series of low-cardinality strings, try
astype('category')") buys two things at once -- much less memory for the key column, and
faster split-apply-combine operations (groupby, value_counts) -- because the key becomes a
handful of distinct values plus small integer codes instead of millions of repeated Python
strings.

PREDICTION: key RAM drops by ~the row/cardinality ratio; groupby is moderately faster;
value_counts (which is almost pure key-bucketing) is faster still.

VERDICT (measured): CONFIRMED. On 3M rows over 20 distinct keys, the key column shrinks ~50x,
groupby-mean runs ~3x faster, and value_counts runs ~15-19x faster.

Run:  .venv/bin/python chapter_7/hypothesis/h01_category_groupby/bench.py
Plot: .venv/bin/python chapter_7/hypothesis/h01_category_groupby/bench.py --plot
"""
import pathlib
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

N = 3_000_000        # rows
CARDINALITY = 20     # distinct key values -> low cardinality, the regime category targets


def best(fn, reps=5, warmup=1):
    for _ in range(warmup):
        fn()
    b = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        b = min(b, time.perf_counter() - t)
    return b


def make_frames(seed=0):
    rng = np.random.default_rng(seed)
    cats = [f"type_{i:02d}" for i in range(CARDINALITY)]
    keys = rng.choice(cats, size=N)
    v = rng.random(N)
    df_obj = pd.DataFrame({"k": pd.Series(keys, dtype="object"), "v": v})
    df_cat = df_obj.copy()
    df_cat["k"] = df_cat["k"].astype("category")
    return df_obj, df_cat


def collect():
    df_obj, df_cat = make_frames()
    mem_obj = df_obj["k"].memory_usage(deep=True) / 1e6
    mem_cat = df_cat["k"].memory_usage(deep=True) / 1e6

    gb_obj = best(lambda: df_obj.groupby("k")["v"].mean()) * 1e3
    gb_cat = best(lambda: df_cat.groupby("k", observed=True)["v"].mean()) * 1e3
    vc_obj = best(lambda: df_obj["k"].value_counts()) * 1e3
    vc_cat = best(lambda: df_cat["k"].value_counts()) * 1e3
    return {
        "mem": (mem_obj, mem_cat),
        "groupby": (gb_obj, gb_cat),
        "value_counts": (vc_obj, vc_cat),
    }


def report(data):
    mo, mc = data["mem"]
    go, gc = data["groupby"]
    vo, vc = data["value_counts"]
    print(f"{N:,} rows over {CARDINALITY} distinct keys -- object vs category:\n")
    print(f"  key column RAM : object {mo:7.1f} MB   category {mc:6.1f} MB   ({mo / mc:4.1f}x smaller)")
    print(f"  groupby-mean   : object {go:7.1f} ms   category {gc:6.1f} ms   ({go / gc:4.1f}x faster)")
    print(f"  value_counts   : object {vo:7.1f} ms   category {vc:6.1f} ms   ({vo / vc:4.1f}x faster)")
    print("\n-> category stores each distinct key once plus tiny integer codes, so it is both")
    print("   far lighter and faster to bucket -- most dramatically for value_counts.")


def plot(data, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))

    # Left: key-column memory (log).
    mo, mc = data["mem"]
    bars = ax1.bar(["object", "category"], [mo, mc], color=["#d62728", "#2ca02c"])
    ax1.set_yscale("log"); ax1.set_ylabel("key column RAM (MB, log)")
    ax1.set_title(f"Key memory — {mo / mc:.0f}× smaller", fontweight="bold")
    for b, val in zip(bars, [mo, mc]):
        ax1.text(b.get_x() + b.get_width() / 2, val * 1.1, f"{val:,.1f}", ha="center", va="bottom", fontsize=10)

    # Right: operation speed (grouped bars).
    go, gc = data["groupby"]
    vo, vc = data["value_counts"]
    x = np.arange(2); w = 0.38
    b1 = ax2.bar(x - w / 2, [go, vo], w, color="#d62728", label="object")
    b2 = ax2.bar(x + w / 2, [gc, vc], w, color="#2ca02c", label="category")
    ax2.set_yscale("log"); ax2.set_ylabel("time (ms, log)")
    ax2.set_xticks(x); ax2.set_xticklabels([f"groupby\n({go / gc:.1f}×)", f"value_counts\n({vo / vc:.1f}×)"])
    ax2.set_title("Operation speed — category wins both", fontweight="bold")
    ax2.legend(fontsize=9)
    for bars_, vals in ((b1, [go, vo]), (b2, [gc, vc])):
        for b, val in zip(bars_, vals):
            ax2.text(b.get_x() + b.get_width() / 2, val * 1.1, f"{val:.0f}", ha="center", va="bottom", fontsize=8)

    fig.suptitle(f"H1 — astype('category') on {N // 1_000_000}M rows, {CARDINALITY} distinct keys: "
                 "lighter AND faster", fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=130)
    print(f"saved {path}")


def main():
    data = collect()
    report(data)
    if "--plot" in sys.argv:
        plot(data, pathlib.Path(__file__).with_name("h01_category_groupby.png"))


if __name__ == "__main__":
    main()
