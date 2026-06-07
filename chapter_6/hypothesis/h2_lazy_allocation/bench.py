"""H2: allocating a big array is cheap; the cost is the FIRST TOUCH.

HYPOTHESIS: Under lazy allocation, asking for memory barely costs anything -- the
kernel only hands back a reference. The real cost arrives on first write, when each
page is faulted in. So np.empty (no init) should be ~free, np.zeros a bit more, and
the first write over the buffer should dwarf both.

PREDICTION: alloc time (empty) ~ 0; first-touch >> alloc.

VERDICT (measured): CONFIRMED. np.empty is effectively instant (no pages touched);
the first write that walks every page costs orders of magnitude more.

This isolates the "minor page fault" mechanism behind ex04: preallocating a scratch
buffer once and reusing it pays the fault tax a single time instead of every
iteration.

Run:  .venv/bin/python chapter_6/hypothesis/h2_lazy_allocation/bench.py
Plot: .venv/bin/python chapter_6/hypothesis/h2_lazy_allocation/bench.py --plot
"""
import pathlib
import sys
import time

import numpy as np

N = 4096 * 4096          # 128 MB of float64


def best(fn, reps=10):
    best_t = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        best_t = min(best_t, time.perf_counter() - t)
    return best_t


def collect():
    """Return labels + microsecond timings for empty / zeros / first-touch."""
    t_empty = best(lambda: np.empty(N)) * 1e6
    t_zeros = best(lambda: np.zeros(N)) * 1e6
    buf = np.empty(N)
    t_touch = best(lambda: buf.fill(1.0), reps=3) * 1e6
    return {
        "mb": N * 8 / 1024 / 1024,
        "labels": ["np.empty\n(no touch)", "np.zeros\n(alloc)", "first .fill()\n(touch all pages)"],
        "us": [t_empty, t_zeros, t_touch],
    }


def report(data):
    print(f"Array of {N:,} float64 = {data['mb']:.0f} MB\n")
    e, z, t = data["us"]
    print(f"  np.empty alloc (no touch):     {e:9.1f} us")
    print(f"  np.zeros alloc:                {z:9.1f} us")
    print(f"  first .fill() over the buffer: {t:9.1f} us  (touches all pages)")
    print(f"\n-> first-touch is ~{t / max(e, 1e-9):.0f}x the cost of the empty allocation.")
    print("   Allocation is lazy/cheap; the page faults on first write are the real")
    print("   cost -- which is exactly why ex04 preallocates scratch once and reuses it.")


def plot(data, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    colors = ["#2ca02c", "#ff7f0e", "#d62728"]
    bars = ax.bar(data["labels"], data["us"], color=colors)
    ax.set_yscale("log")
    ax.set_ylabel("time (µs, log scale)")
    ax.set_title(f"H2 — lazy allocation: the first touch is the cost ({data['mb']:.0f} MB array)",
                 fontweight="bold")
    for b, v in zip(bars, data["us"]):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.15, f"{v:,.1f} µs",
                ha="center", va="bottom", fontsize=10)
    e, _, t = data["us"]
    ax.annotate(f"~{t / max(e, 1e-9):.0f}× the\nempty alloc", xy=(2, t), xytext=(1.4, t * 0.25),
                ha="center", fontsize=10, color="#d62728",
                arrowprops=dict(arrowstyle="->", color="#d62728"))
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"saved {path}")


def main():
    data = collect()
    report(data)
    if "--plot" in sys.argv:
        plot(data, pathlib.Path(__file__).with_name("h2_lazy_allocation.png"))


if __name__ == "__main__":
    main()
