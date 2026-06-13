"""H5: under pandas 3.0 Copy-on-Write, a copy is lazy -- the cost lands on first write.

HYPOTHESIS: With Copy-on-Write (the default in pandas 3.0), a shallow copy
(`df.copy(deep=False)`) barely costs anything -- the new frame shares the original's data
buffers and only promises to copy if you write. The real cost is deferred to the first
mutation, and even then only the *touched* column is duplicated, not the whole frame. A deep
copy, by contrast, pays for the entire frame up front.

PREDICTION: shallow copy ~ free; deep copy >> shallow; a single post-copy write costs about
one column's worth (≈ deep / n_columns), not a whole frame -- and CoW keeps the original
safely unchanged.

VERDICT (measured): CONFIRMED. On 5M rows x 10 float columns, a shallow copy is ~1000x cheaper
than a deep copy, and the first write materializes roughly a single column -- while the
original frame is left untouched (the safety CoW buys you for free).

This is the pandas mirror of chapter 6's "lazy allocation" hypothesis: getting the thing is
cheap; the bill comes due on first use.

Run:  .venv/bin/python chapter_7/hypothesis/h05_cow_lazy_copy/bench.py
Plot: .venv/bin/python chapter_7/hypothesis/h05_cow_lazy_copy/bench.py --plot
"""
import pathlib
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROWS = 5_000_000
COLS = 10


def best(fn, reps=3, warmup=1):
    for _ in range(warmup):
        fn()
    b = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        b = min(b, time.perf_counter() - t)
    return b


def make_df(seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({f"c{i}": rng.random(ROWS) for i in range(COLS)})


def collect():
    df = make_df()

    t_deep = best(lambda: df.copy(), reps=3) * 1e3            # eager full-frame copy
    t_shallow = best(lambda: df.copy(deep=False), reps=5) * 1e3  # lazy: shares buffers

    def shallow_then_write():
        d = df.copy(deep=False)
        d.iloc[0, 0] = 1.234      # first write triggers CoW materialization of the touched data
        return d

    t_write = best(shallow_then_write, reps=3) * 1e3

    # Safety check: under CoW, mutating the shallow copy must NOT change the original.
    original_first = df.iloc[0, 0]
    d = df.copy(deep=False)
    d.iloc[0, 0] = -999.0
    cow_safe = df.iloc[0, 0] == original_first

    return {
        "deep_ms": t_deep,
        "shallow_ms": t_shallow,
        "write_ms": t_write,
        "cow_safe": bool(cow_safe),
    }


def report(data):
    print(f"DataFrame: {ROWS:,} rows x {COLS} float64 columns ({ROWS * COLS * 8 / 1e6:.0f} MB)\n")
    print(f"  deep copy   df.copy()         : {data['deep_ms']:8.2f} ms   (copies the whole frame)")
    print(f"  shallow     df.copy(deep=False): {data['shallow_ms']:8.4f} ms   "
          f"({data['deep_ms'] / data['shallow_ms']:,.0f}x cheaper -- shares buffers)")
    print(f"  shallow + 1 write             : {data['write_ms']:8.2f} ms   "
          f"(~one column: deep / {data['deep_ms'] / data['write_ms']:.0f})")
    print(f"\n  CoW safety: original unchanged after mutating the shallow copy? {data['cow_safe']}")
    print("  -> the copy is a cheap promise; writing pays for only the column you touch,")
    print("     and the original is protected for free.")


def plot(data, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    labels = ["shallow copy\n(deep=False)", "shallow + 1 write\n(materialize 1 col)", "deep copy\n(whole frame)"]
    vals = [data["shallow_ms"], data["write_ms"], data["deep_ms"]]
    colors = ["#2ca02c", "#ff7f0e", "#d62728"]
    bars = ax.bar(labels, vals, color=colors)
    ax.set_yscale("log")
    ax.set_ylabel("time (ms, log scale)")
    ax.set_title(f"H5 — CoW: the copy is lazy, the write pays ({ROWS // 1_000_000}M×{COLS} floats)",
                 fontweight="bold")
    for b, v in zip(bars, vals):
        txt = f"{v:.4f} ms" if v < 0.1 else f"{v:.2f} ms"
        ax.text(b.get_x() + b.get_width() / 2, v * 1.15, txt, ha="center", va="bottom", fontsize=9)
    ax.annotate(f"~{data['deep_ms'] / data['shallow_ms']:,.0f}× cheaper\nthan a deep copy",
                xy=(0, data["shallow_ms"]), xytext=(0.5, data["shallow_ms"] * 30),
                ha="center", fontsize=9.5, color="#2ca02c",
                arrowprops=dict(arrowstyle="->", color="#2ca02c"))
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"saved {path}")


def main():
    data = collect()
    report(data)
    if "--plot" in sys.argv:
        plot(data, pathlib.Path(__file__).with_name("h05_cow_lazy_copy.png"))


if __name__ == "__main__":
    main()
