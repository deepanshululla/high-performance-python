"""Visualize ex02: set turns an O(n^2) scan into one O(n) pass.

Run: .venv/bin/python chapter_4/ex02_set_vs_list_unique/plot.py
"""
import pathlib
import sys
import timeit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex02_set_vs_list_unique as ex  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402

CAP = "CPython 3.14 / macOS"


def main():
    setup()
    Ns = [1_000, 5_000, 20_000]
    t_list, t_set = [], []
    for N in Ns:
        pb = [(f"Name{i} Last{i}", "555") for i in range(N)]
        t_list.append(min(timeit.repeat(lambda: ex.list_unique_first_names(pb), repeat=3, number=1)))
        t_set.append(min(timeit.repeat(lambda: ex.set_unique_first_names(pb), repeat=3, number=1)))

    fig, ax = plt.subplots(figsize=(8.6, 5.1))
    ax.plot(Ns, t_list, "-o", color=COLORS["red"], lw=2, ms=7, label="list scan (O(n^2)-ish)")
    ax.plot(Ns, t_set, "-o", color=COLORS["teal"], lw=2, ms=7, label="set.add (O(n))")
    ax.set_xscale("log")
    ax.set_yscale("log")
    speed_lo = t_list[0] / t_set[0]
    speed_hi = t_list[-1] / t_set[-1]
    mid = len(Ns) // 2
    ax.annotate(f"gap widens with N\n{speed_lo:.0f}x -> {speed_hi:.0f}x faster",
                xy=(Ns[mid], (t_list[mid] * t_set[mid]) ** 0.5),
                xytext=(Ns[mid] * 1.1, 0.01),
                color=COLORS["red"], fontsize=10, fontweight="bold", ha="center",
                arrowprops=dict(arrowstyle="->", color=COLORS["red"]))
    ax.set_xlabel("N (unique names)")
    ax.set_ylabel("time (s, log)")
    ax.set_title("ex02 - set turns an O(n^2) scan into one O(n) pass")
    ax.legend(loc="lower right")
    save(fig, __file__, name="chart.png",
         subtitle=f"List's inner scan grows with N; set.add stays flat, so the gap widens | {CAP}")


if __name__ == "__main__":
    main()
