"""Visualize ex04: keeping a list sorted (insort) vs searching it (find_closest).

Reuses ex04's own find_closest. Sizes are reduced from the README to keep
runtime reasonable -- the SHAPE/ordering is the point, so exact magnitudes will
differ from the README numbers.

Run: .venv/bin/python chapter_3/ex04_find_closest/plot.py
"""
import bisect
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex04_find_closest as ex  # noqa: E402
from perf import time_s  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402

CPU = "CPython 3.14 / macOS"
NOTE = "exact magnitudes differ from the README (yours will differ)"


def main():
    setup()
    random.seed(1)
    big = sorted(random.randint(0, 10_000_000) for _ in range(200_000))  # README: 1e6
    t_insort = time_s(lambda: bisect.insort(big, 5_000_000), number=100) * 1e6
    t_search = time_s(lambda: ex.find_closest(big, 5_000_000), number=10_000) * 1e6

    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    labels = ["insort\n(keep sorted) O(n)", "find_closest\n(search) O(log n)"]
    vals = [t_insort, t_search]
    bars = ax.bar(labels, vals, color=[COLORS["red"], COLORS["teal"]], width=0.6)
    ax.set_yscale("log")
    ax.set_ylabel("time (microseconds, log scale)")
    ax.set_title("ex04 - Keeping sorted vs searching sorted")
    ax.bar_label(bars, fmt="%.2f us", padding=3, fontsize=10)
    ax.annotate(f"~{t_insort / t_search:,.0f}x",
                xy=(1, t_search), xytext=(0.5, (t_insort * t_search) ** 0.5),
                ha="center", color=COLORS["violet"], fontsize=11, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=COLORS["violet"]))
    ax.set_ylim(top=t_insort * 3)
    save(fig, __file__, name="chart.png",
         subtitle=f"insort shifts O(n) elements; the search is O(log n) | {NOTE} | {CPU}")


if __name__ == "__main__":
    main()
