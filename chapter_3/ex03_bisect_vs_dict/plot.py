"""Visualize ex03: one bisect lookup vs building a set, in time and memory.

Sizes are reduced from the README to keep runtime reasonable -- the
SHAPE/ordering is the point, so exact magnitudes will differ from the README.

Run: .venv/bin/python chapter_3/ex03_bisect_vs_dict/plot.py
"""
import bisect
import pathlib
import random
import sys
import timeit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex03_bisect_vs_dict as ex  # noqa: E402,F401  (imported for parity / side-effect-free)
from vizutil import plt, setup, save, COLORS  # noqa: E402

CPU = "CPython 3.14 / macOS"
NOTE = "exact magnitudes differ from the README (yours will differ)"


def main():
    setup()
    random.seed(0)
    data = sorted(random.sample(range(10_000_000), 200_000))  # README: 1e6
    target = data[123_45]

    def via_bisect():
        i = bisect.bisect_left(data, target)
        return i if i < len(data) and data[i] == target else -1

    def build_then_query():
        s = set(data)
        return target in s

    t_bisect = min(timeit.repeat(via_bisect, number=1000)) / 1000 * 1e6
    t_build = min(timeit.repeat(build_then_query, number=10)) / 10 * 1e6
    s = set(data)
    t_member = min(timeit.repeat(lambda: target in s, number=1_000_000)) / 1e6 * 1e6

    mem_list = sys.getsizeof(data) / 1e6
    mem_set = sys.getsizeof(s) / 1e6

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6))

    labels = ["bisect\nlookup", "set build\n+ 1 query", "prebuilt set\nmembership"]
    vals = [t_bisect, t_build, t_member]
    bars = ax1.bar(labels, vals, color=[COLORS["teal"], COLORS["red"], COLORS["blue"]], width=0.62)
    ax1.set_yscale("log")
    ax1.set_ylabel("time per query (microseconds, log scale)")
    ax1.set_title("Time: build cost dwarfs a lookup")
    ax1.bar_label(bars, fmt="%.3f us", padding=3, fontsize=9.5)

    mbars = ax2.bar(["sorted list", "set"], [mem_list, mem_set],
                    color=[COLORS["teal"], COLORS["red"]], width=0.55)
    ax2.set_ylabel("memory (MB)")
    ax2.set_title("Memory: the hash table is much larger")
    ax2.bar_label(mbars, fmt="%.1f MB", padding=3, fontsize=10)
    ax2.annotate(f"~{mem_set / mem_list:.1f}x memory\nfor O(1) lookup",
                 xy=(1, mem_set), xytext=(0.5, mem_set * 0.55),
                 ha="center", color=COLORS["violet"], fontsize=10, fontweight="bold")

    fig.suptitle("ex03 - bisect vs set: one lookup vs amortized O(1)",
                 fontsize=13, fontweight="bold")
    save(fig, __file__, name="chart.png",
         subtitle=f"bisect wins for a single query; the set trades memory for O(1) at scale | {NOTE} | {CPU}")


if __name__ == "__main__":
    main()
