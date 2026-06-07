"""Visualize ex09: native __lt__ vs total_ordering-derived comparison cost.

Reuses ex09's Card. Exact magnitudes will differ from the README numbers
(yours will differ) -- the SHAPE/ordering is the point.

Run: .venv/bin/python chapter_3/ex09_custom_ordering/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex09_custom_ordering as ex  # noqa: E402
from perf import time_s  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402

CPU = "CPython 3.14 / macOS"
NOTE = "exact magnitudes differ from the README (yours will differ)"


def main():
    setup()
    a, b = ex.Card("K", "H"), ex.Card("Q", "S")
    t_lt = time_s(lambda: a < b, number=1_000_000) * 1e9
    t_ge = time_s(lambda: a >= b, number=1_000_000) * 1e9

    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    labels = ["a < b\nnative __lt__", "a >= b\ntotal_ordering"]
    vals = [t_lt, t_ge]
    bars = ax.bar(labels, vals, color=[COLORS["teal"], COLORS["amber"]], width=0.55)
    ax.set_ylabel("ns / op")
    ax.set_title("ex09 - native __lt__ vs total_ordering-derived")
    ax.bar_label(bars, fmt="%.1f ns", padding=3, fontsize=10)
    ax.set_ylim(top=max(vals) * 1.2)
    ax.annotate(f"+{t_ge - t_lt:.0f} ns\n(call indirection)",
                xy=(1, t_ge), xytext=(0.5, max(vals) * 1.08),
                ha="center", color=COLORS["violet"], fontsize=10, fontweight="bold")
    save(fig, __file__, name="chart.png",
         subtitle=f"total_ordering derives >= from __lt__/__eq__ at a small per-call cost | {NOTE} | {CPU}")


if __name__ == "__main__":
    main()
