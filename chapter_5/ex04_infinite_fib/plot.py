"""Visualize ex04: count odd Fibonaccis < 5,000 three ways -- all agree, all O(1).

Reuses the exercise's own count_naive / count_transform / count_succinct.

Run: .venv/bin/python chapter_5/ex04_infinite_fib/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex04_infinite_fib as ex  # noqa: E402  (sibling; its dir is sys.path[0])
from perf import time_s  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402

CAP = "CPython 3.14 / macOS"


def _bar_time(ax, labels, vals, colors, ylabel, title, fmt="%.1f"):
    bars = ax.bar(labels, vals, color=colors, width=0.55)
    ax.bar_label(bars, fmt=fmt, padding=3, fontsize=9.5)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_ylim(0, max(vals) * 1.25)


def main():
    setup()
    names = ["naive", "transform", "succinct\n(takewhile)"]
    fns = [ex.count_naive, ex.count_transform, ex.count_succinct]
    vals = [time_s(fn, number=10_000) * 1e6 for fn in fns]

    fig, ax = plt.subplots(figsize=(8.6, 5.1))
    _bar_time(ax, names, vals,
              [COLORS["teal"], COLORS["blue"], COLORS["violet"]],
              "us / call", "ex04 - count odd Fibonaccis < 5,000: three ways", fmt="%.2f")
    save(fig, __file__,
         subtitle=f"All three agree and are O(1) memory; succinct/takewhile trades a little CPU for clarity | {CAP}",
         name="chart.png")


if __name__ == "__main__":
    main()
