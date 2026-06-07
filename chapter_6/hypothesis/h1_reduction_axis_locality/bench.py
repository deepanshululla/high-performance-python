"""H1: "reduce along the contiguous axis and it's faster" -- is the naive cache
intuition right for numpy reductions?

HYPOTHESIS: For a C-contiguous 2D array, sum(axis=1) (reduce along contiguous
rows) should beat sum(axis=0) (reduce along the strided column direction),
because contiguous access is cache-friendly -- and the gap should widen with size.

PREDICTION (naive): axis=1 faster at every size, increasingly so.

VERDICT (measured): FALSE until very large sizes. numpy implements the axis=0
reduction as vectorized accumulation INTO a contiguous row buffer -- adding whole
rows together -- which is more SIMD-friendly than collapsing each contiguous row
to a single scalar. So the "strided" reduction is actually FASTER until the
working set overflows cache (~8192x8192 here), where locality finally reasserts.

Lesson: data-locality intuition is necessary but not sufficient. HOW a library
vectorizes the loop can dominate the raw access pattern. Benchmark, don't assume.

Run:  .venv/bin/python chapter_6/hypothesis/h1_reduction_axis_locality/bench.py
Plot: .venv/bin/python chapter_6/hypothesis/h1_reduction_axis_locality/bench.py --plot
"""
import pathlib
import sys
import time

import numpy as np

SIZES = (1024, 2048, 4096, 8192)


def best(fn, reps=5):
    best_t = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        best_t = min(best_t, time.perf_counter() - t)
    return best_t


def collect():
    """Return {'sizes', 'contig' (axis=1 ms), 'strided' (axis=0 ms)}."""
    contig, strided = [], []
    for n in SIZES:
        a = np.random.rand(n, n)
        assert np.allclose(a.sum(axis=1).sum(), a.sum(axis=0).sum())
        contig.append(best(lambda a=a: a.sum(axis=1)) * 1e3)
        strided.append(best(lambda a=a: a.sum(axis=0)) * 1e3)
    return {"sizes": list(SIZES), "contig": contig, "strided": strided}


def report(data):
    print("C-contiguous 2D array: axis=1 reduces ALONG contiguous rows;")
    print("axis=0 reduces ACROSS rows (the 'strided' direction).\n")
    print(f"{'size':>11}  {'axis=1 (contig)':>16}  {'axis=0 (strided)':>17}  verdict")
    for n, t1, t0 in zip(data["sizes"], data["contig"], data["strided"]):
        if t0 < t1:
            verdict = f"strided FASTER ({t1 / t0:.2f}x) -- intuition WRONG"
        else:
            verdict = f"contig faster ({t0 / t1:.2f}x) -- intuition holds"
        print(f"{n:>5}x{n:<5}  {t1:13.2f} ms  {t0:14.2f} ms  {verdict}")
    print("\n-> The naive 'contiguous axis wins' prediction is backwards at small/mid")
    print("   sizes: numpy's axis=0 reduction accumulates whole rows (vectorized) into a")
    print("   contiguous buffer. Locality only wins once the array overflows cache.")


def plot(data, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sizes = data["sizes"]
    x = range(len(sizes))
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    ax.plot(x, data["contig"], "o-", color="#1f77b4", label="axis=1 (contiguous)")
    ax.plot(x, data["strided"], "s-", color="#d62728", label="axis=0 (strided)")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{n}²" for n in sizes])
    ax.set_ylabel("time (ms, lower is better)")
    ax.set_title("Reduction time by axis")
    ax.legend()
    ax.grid(True, alpha=0.3)

    ratio = [s / c for s, c in zip(data["strided"], data["contig"])]
    colors = ["#2ca02c" if r < 1 else "#d62728" for r in ratio]
    ax2.bar(x, ratio, color=colors)
    ax2.axhline(1.0, color="black", lw=1, ls="--")
    ax2.set_xticks(list(x))
    ax2.set_xticklabels([f"{n}²" for n in sizes])
    ax2.set_ylabel("strided / contiguous")
    ax2.set_title("<1 (green) = strided faster = intuition WRONG")
    for xi, r in zip(x, ratio):
        ax2.text(xi, r + 0.01, f"{r:.2f}", ha="center", va="bottom", fontsize=9)
    ax2.grid(True, axis="y", alpha=0.3)

    fig.suptitle("H1 — contiguous vs strided reduction axis (numpy, M1 Max)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"saved {path}")


def main():
    data = collect()
    report(data)
    if "--plot" in sys.argv:
        plot(data, pathlib.Path(__file__).with_name("h1_reduction_axis.png"))


if __name__ == "__main__":
    main()
