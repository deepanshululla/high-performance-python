"""Visualize H1: `yield from` vs manual re-yield (per-item cost).

Run: .venv/bin/python chapter_5/hypothesis/h01_yield_from_overhead/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import benchmark as B  # noqa: E402
from perf import time_s  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402


def main():
    setup()
    t_yf = time_s(lambda: sum(B.via_yield_from(B.N)), number=1, repeat=7) / B.N * 1e9
    t_manual = time_s(lambda: sum(B.via_manual(B.N)), number=1, repeat=7) / B.N * 1e9

    fig, ax = plt.subplots(figsize=(6.8, 5))
    labels = ["yield from\ninner(n)", "for x in inner(n):\n    yield x"]
    vals = [t_yf, t_manual]
    bars = ax.bar(labels, vals, color=[COLORS["teal"], COLORS["amber"]], width=0.55)
    ax.bar_label(bars, fmt="%.1f ns", padding=3, fontsize=11)
    ax.annotate(f"{t_manual/t_yf:.2f}x faster\n(delegates in C)",
                xy=(0, t_yf), xytext=(0.5, t_yf * 0.55), ha="center",
                color=COLORS["teal"], fontsize=10.5,
                arrowprops=dict(arrowstyle="->", color=COLORS["teal"]))
    ax.set_ylabel("ns / item")
    ax.set_ylim(0, max(vals) * 1.2)
    ax.set_title("H1 - `yield from` vs manual re-yield (1 delegating layer)")
    save(fig, __file__,
         subtitle="CONFIRMED but modest (1.13x) at one hop - the gap compounds with depth (see H2) | CPython 3.14 / macOS")


if __name__ == "__main__":
    main()
