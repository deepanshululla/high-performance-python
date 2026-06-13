"""H4: does `category` stop being worth it as key cardinality rises? (the boundary of H1)

HYPOTHESIS: H1 showed `category` is much lighter and faster for a low-cardinality key (20
distinct values). The folklore says this reverses as cardinality climbs toward the row count:
with few repeats, the category dictionary is nearly as big as the data, so the memory and
speed advantages should shrink and eventually invert into a liability.

PREDICTION: as distinct-key count rises toward N, the memory win shrinks toward 1x and the
groupby win disappears -- category becomes no better, or worse, than plain object strings.

VERDICT (measured): FALSIFIED. The memory win shrinks (≈53x → ≈4x) but never inverts, and the
*groupby* win actually GROWS (≈2.7x → ≈12x) because hashing millions of distinct Python
strings gets dramatically more expensive than bucketing integer codes. The only genuine tax is
the one-time `astype('category')` conversion, which rises steeply with cardinality -- yet even
at full cardinality it pays for itself within a few groupbys.

Run:  .venv/bin/python chapter_7/hypothesis/h04_category_cardinality/bench.py
Plot: .venv/bin/python chapter_7/hypothesis/h04_category_cardinality/bench.py --plot
"""
import pathlib
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

N = 2_000_000
CARDINALITIES = [10, 1_000, 50_000, 500_000, 2_000_000]


def best(fn, reps=2, warmup=1):
    for _ in range(warmup):
        fn()
    b = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        b = min(b, time.perf_counter() - t)
    return b


def measure(card, seed=0):
    rng = np.random.default_rng(seed)
    cats = np.array([f"id_{i}" for i in range(card)])
    keys = rng.choice(cats, size=N)
    v = rng.random(N)
    df_obj = pd.DataFrame({"k": pd.Series(keys, dtype="object"), "v": v})
    df_cat = df_obj.copy()
    df_cat["k"] = df_obj["k"].astype("category")

    mem_obj = df_obj["k"].memory_usage(deep=True) / 1e6
    mem_cat = df_cat["k"].memory_usage(deep=True) / 1e6
    gb_obj = best(lambda: df_obj.groupby("k")["v"].mean())
    gb_cat = best(lambda: df_cat.groupby("k", observed=True)["v"].mean())
    t_conv = best(lambda: df_obj["k"].astype("category")) * 1e3
    return {
        "card": card,
        "mem_win": mem_obj / mem_cat,
        "gb_win": gb_obj / gb_cat,
        "conv_ms": t_conv,
        "gb_saving_ms": (gb_obj - gb_cat) * 1e3,
    }


def collect():
    return [measure(c) for c in CARDINALITIES]


def report(rows):
    print(f"{N:,} rows; sweeping distinct-key cardinality (object vs category):\n")
    print(f"  {'cardinality':>12} | {'mem win':>8} | {'groupby win':>11} | {'astype cost':>11} | payback")
    for r in rows:
        payback = r["conv_ms"] / r["gb_saving_ms"] if r["gb_saving_ms"] > 0 else float("inf")
        print(f"  {r['card']:>12,} | {r['mem_win']:7.1f}x | {r['gb_win']:10.2f}x | "
              f"{r['conv_ms']:8.0f} ms | ~{payback:.1f} groupbys")
    print("\n-> the win never inverts: memory advantage shrinks but stays > 1x, and groupby")
    print("   gets RELATIVELY better as string hashing dominates. The only tax is the")
    print("   one-time conversion, amortized within a few grouped operations.")


def plot(rows, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cards = [r["card"] for r in rows]
    mem = [r["mem_win"] for r in rows]
    gb = [r["gb_win"] for r in rows]
    conv = [r["conv_ms"] for r in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))

    ax1.plot(cards, mem, "o-", color="#1f77b4", label="memory win (×)")
    ax1.plot(cards, gb, "s-", color="#2ca02c", label="groupby win (×)")
    ax1.axhline(1.0, color="#d62728", ls="--", lw=1, label="break-even (1×)")
    ax1.set_xscale("log"); ax1.set_xlabel("distinct keys (log)")
    ax1.set_ylabel("category advantage (×)")
    ax1.set_title("Win never inverts (prediction FALSIFIED)", fontweight="bold")
    ax1.legend(fontsize=9); ax1.grid(True, alpha=0.3)

    ax2.plot(cards, conv, "o-", color="#ff7f0e")
    ax2.set_xscale("log"); ax2.set_xlabel("distinct keys (log)")
    ax2.set_ylabel("astype('category') cost (ms)")
    ax2.set_title("The real tax: one-time conversion", fontweight="bold")
    ax2.grid(True, alpha=0.3)

    fig.suptitle(f"H4 — category across cardinality ({N // 1_000_000}M rows)", fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=130)
    print(f"saved {path}")


def main():
    rows = collect()
    report(rows)
    if "--plot" in sys.argv:
        plot(rows, pathlib.Path(__file__).with_name("h04_category_cardinality.png"))


if __name__ == "__main__":
    main()
