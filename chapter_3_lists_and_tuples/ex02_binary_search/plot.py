"""Visualize ex02: binary search vs linear scan on a worst-case miss.

Reuses ex02's own benchmarked functions. Sizes are reduced from the README to
keep runtime reasonable -- the SHAPE/ordering is the point, so exact magnitudes
will differ from the README numbers.

Run: .venv/bin/python chapter_3/ex02_binary_search/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex02_binary_search as ex  # noqa: E402
from perf import time_s  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402

CPU = "CPython 3.14 / macOS"
NOTE = "exact magnitudes differ from the README (yours will differ)"


def main():
    setup()
    big = list(range(200_000))            # README uses 1e6; shape is identical
    miss = -1
    t_lin = time_s(lambda: ex.linear_search(miss, big), number=5) * 1e6
    t_bin = time_s(lambda: ex.binary_search(miss, big), number=1000) * 1e6

    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    labels = ["linear_search\nO(n)", "binary_search\nO(log n)"]
    vals = [t_lin, t_bin]
    bars = ax.bar(labels, vals, color=[COLORS["red"], COLORS["teal"]], width=0.6)
    ax.set_yscale("log")
    ax.set_ylabel("time per query (microseconds, log scale)")
    ax.set_title("ex02 - Binary search vs linear scan (worst-case miss)")
    ax.bar_label(bars, fmt="%.2f us", padding=3, fontsize=10)
    speedup = t_lin / t_bin
    ax.annotate(f"~{speedup:,.0f}x faster",
                xy=(1, t_bin), xytext=(0.5, (t_lin * t_bin) ** 0.5),
                ha="center", color=COLORS["violet"], fontsize=11, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=COLORS["violet"]))
    ax.set_ylim(top=t_lin * 3)
    save(fig, __file__, name="chart.png",
         subtitle=f"sorted-order search collapses O(n) to O(log n) | {NOTE} | {CPU}")


if __name__ == "__main__":
    main()
