"""Visualize H3: native generators vs a hand-rolled __next__ class (per-item cost).

Run: .venv/bin/python chapter_5/hypothesis/h03_iterator_impls/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import benchmark as B  # noqa: E402
from perf import time_s  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402


def main():
    setup()
    variants = [
        ("generator\nexpression", lambda: sum(B.gen_expr(B.N)), COLORS["teal"]),
        ("generator\nfunction", lambda: sum(B.gen_func(B.N)), COLORS["blue"]),
        ("class\n__iter__/__next__", lambda: sum(B.GenClass(B.N)), COLORS["red"]),
    ]
    labels = [v[0] for v in variants]
    vals = [time_s(v[1], number=1, repeat=7) / B.N * 1e9 for v in variants]
    colors = [v[2] for v in variants]

    fig, ax = plt.subplots(figsize=(7.4, 5))
    bars = ax.bar(labels, vals, color=colors, width=0.6)
    ax.bar_label(bars, fmt="%.1f ns", padding=3, fontsize=11)
    ax.annotate(f"{vals[-1]/min(vals):.1f}x slower\n(Python __next__ call\n+ self attr access)",
                xy=(2, vals[-1]), xytext=(1.2, vals[-1] * 0.62), ha="center",
                color=COLORS["red"], fontsize=10,
                arrowprops=dict(arrowstyle="->", color=COLORS["red"]))
    ax.set_ylabel("ns / item")
    ax.set_ylim(0, max(vals) * 1.2)
    ax.set_title(f"H3 - Three iterator implementations ({B.N:,} items)")
    save(fig, __file__,
         subtitle="CONFIRMED - the __next__ class is 2.8x slower than the C-level generator path | CPython 3.14 / macOS")


if __name__ == "__main__":
    main()
