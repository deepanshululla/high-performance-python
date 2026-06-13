"""Visualize ex07: list vs tuple instantiation across the size-20 freelist boundary.

Sizes are reduced from the README to keep runtime reasonable -- the
SHAPE/ordering is the point, so exact magnitudes will differ from the README.

Run: .venv/bin/python chapter_3/ex07_instantiation_timing/plot.py
"""
import pathlib
import sys
import timeit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex07_instantiation_timing as ex  # noqa: E402,F401  (imported for parity)
from vizutil import plt, setup, save, COLORS  # noqa: E402

CPU = "CPython 3.14 / macOS"
NOTE = "exact magnitudes differ from the README (yours will differ)"


def main():
    setup()
    n = 2_000_000  # README: 1e7; ordering is what matters
    t_list = timeit.timeit("[0,1,2,3,4,5,6,7,8,9]", number=n) / n * 1e9
    t_tuple = timeit.timeit("(0,1,2,3,4,5,6,7,8,9)", number=n) / n * 1e9
    big_list = timeit.timeit("list(r)", setup="r=range(30)", number=n) / n * 1e9
    big_tuple = timeit.timeit("tuple(r)", setup="r=range(30)", number=n) / n * 1e9

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    groups = ["size-10 literal", "*(range(30)) build"]
    x = range(len(groups))
    w = 0.36
    lvals = [t_list, big_list]
    tvals = [t_tuple, big_tuple]
    b1 = ax.bar([i - w / 2 for i in x], lvals, w, label="list", color=COLORS["red"])
    b2 = ax.bar([i + w / 2 for i in x], tvals, w, label="tuple", color=COLORS["teal"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(groups)
    ax.set_ylabel("ns / op")
    ax.set_title("ex07 - list vs tuple instantiation: freelist boundary")
    ax.bar_label(b1, fmt="%.1f", padding=3, fontsize=9)
    ax.bar_label(b2, fmt="%.1f", padding=3, fontsize=9)
    ax.legend()
    ax.text(0, max(lvals[0], tvals[0]) * 1.22, "tuple wins\n(<=20: freelist)",
            ha="center", color=COLORS["teal"], fontsize=9.5)
    ax.text(1, max(lvals[1], tvals[1]) * 1.12, "gap reverses\n(>20: no freelist)",
            ha="center", color=COLORS["red"], fontsize=9.5)
    ax.set_ylim(top=max(max(lvals), max(tvals)) * 1.4)
    save(fig, __file__, name="chart.png",
         subtitle=f"tuple literal wins at size 10; past the size-20 freelist the advantage reverses | {NOTE} | {CPU}")


if __name__ == "__main__":
    main()
