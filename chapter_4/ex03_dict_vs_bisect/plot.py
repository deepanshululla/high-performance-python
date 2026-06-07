"""Visualize ex03: dict stays flat (O(1)) while bisect rises (O(log n)).

Run: .venv/bin/python chapter_4/ex03_dict_vs_bisect/plot.py
"""
import pathlib
import random
import sys
import timeit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex03_dict_vs_bisect as ex  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402

CAP = "CPython 3.14 / macOS"


def main():
    setup()
    random.seed(0)
    Ns = [1_000, 100_000, 1_000_000]
    t_bisect, t_dict = [], []
    names = numbers = d = None
    N = Ns[-1]
    for N in Ns:
        names, numbers, d = ex.build(N)
        key = names[N // 2]
        t_bisect.append(min(timeit.repeat(lambda: ex.lookup_bisect(names, numbers, key), repeat=5, number=10_000)))
        t_dict.append(min(timeit.repeat(lambda: d[key], repeat=5, number=10_000)))

    assert names is not None and numbers is not None and d is not None
    lists_mb = (sys.getsizeof(names) + sys.getsizeof(numbers)) / 1e6
    dict_mb = sys.getsizeof(d) / 1e6

    fig, (axl, axr) = plt.subplots(1, 2, figsize=(11.0, 5.0))
    axl.plot(Ns, t_dict, "-o", color=COLORS["teal"], lw=2, ms=7, label="dict O(1)")
    axl.plot(Ns, t_bisect, "-o", color=COLORS["blue"], lw=2, ms=7, label="list+bisect O(log n)")
    axl.set_xscale("log")
    axl.set_xlabel("N")
    axl.set_ylabel("time per 10k lookups (s)")
    axl.set_title("ex03 - dict stays flat; bisect rises")
    axl.legend(loc="upper left")

    bars = axr.bar(["list+bisect\n(names+numbers)", "dict\n(table only)"],
                   [lists_mb, dict_mb], color=[COLORS["blue"], COLORS["teal"]], width=0.6)
    axr.bar_label(bars, fmt="%.1f MB", padding=3)
    axr.set_ylabel("memory (MB)")
    axr.set_title(f"Memory price of O(1)  (N={N:,})")
    axr.set_ylim(0, max(lists_mb, dict_mb) * 1.25)
    save(fig, __file__, name="chart.png",
         subtitle=f"dict buys flat O(1) lookup by spending ~2x memory on a hash table | {CAP}")


if __name__ == "__main__":
    main()
