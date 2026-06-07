"""Visualize ex06: peak memory of comprehension vs list([...]) vs tuple([...]).

Reuses ex06's total_size. Sizes are reduced from the README to keep runtime
reasonable -- the SHAPE/ordering is the point, so exact magnitudes will differ
from the README numbers.

Run: .venv/bin/python chapter_3/ex06_memory_comp_list_tuple/plot.py
"""
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex06_memory_comp_list_tuple as ex  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402

CPU = "CPython 3.14 / macOS"
NOTE = "exact magnitudes differ from the README (yours will differ)"


def main():
    setup()
    N, k = 200_000, 9
    random.seed(0)
    comp = [[random.randint(0, 100) for _ in range(k)] for _ in range(N)]
    listed = [list([random.randint(0, 100) for _ in range(k)]) for _ in range(N)]
    tupled = [tuple([random.randint(0, 100) for _ in range(k)]) for _ in range(N)]
    s_comp = ex.total_size(comp) / 1e6
    s_list = ex.total_size(listed) / 1e6
    s_tup = ex.total_size(tupled) / 1e6

    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    labels = ["comprehension", "list([...])", "tuple([...])"]
    vals = [s_comp, s_list, s_tup]
    bars = ax.bar(labels, vals, color=[COLORS["red"], COLORS["amber"], COLORS["teal"]], width=0.6)
    ax.set_ylabel("peak memory (MB)")
    ax.set_title("ex06 - Memory: comp > list() > tuple")
    ax.bar_label(bars, fmt="%.1f MB", padding=3, fontsize=10)
    ax.set_ylim(top=s_comp * 1.18)
    ax.annotate(f"{s_comp / s_list:.2f}x", xy=(1, s_list), xytext=(0.5, s_comp * 1.05),
                ha="center", color=COLORS["violet"], fontsize=10, fontweight="bold")
    ax.annotate(f"{s_comp / s_tup:.2f}x", xy=(2, s_tup), xytext=(2, s_comp * 1.05),
                ha="center", color=COLORS["violet"], fontsize=10, fontweight="bold")
    save(fig, __file__, name="chart.png",
         subtitle=f"list() drops append headroom; tuple also drops the resize-bookkeeping word | {NOTE} | {CPU}")


if __name__ == "__main__":
    main()
