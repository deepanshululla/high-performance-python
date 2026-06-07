"""Visualize ex06: a bad hash collapses dict lookup (time), not memory.

Run: .venv/bin/python chapter_4/ex06_good_bad_hash/plot.py
"""
import pathlib
import string
import sys
import timeit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex06_good_bad_hash as ex  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402

CAP = "CPython 3.14 / macOS"


def main():
    setup()
    # reuse BadHash/GoodHash from the exercise; reduced from 1M -> 200k tests (shape holds)
    bad, good, lst = set(), set(), []
    for a in string.ascii_lowercase:
        for b in string.ascii_lowercase:
            bad.add(ex.BadHash(a + b))
            good.add(ex.GoodHash(a + b))
            lst.append(a + b)
    N = 200_000
    g = {"bad": bad, "good": good, "lst": lst, "BadHash": ex.BadHash, "GoodHash": ex.GoodHash}
    t_good = min(timeit.repeat("GoodHash('zz') in good", globals=g, number=N))
    t_list = min(timeit.repeat("'zz' in lst", globals=g, number=N))
    t_bad = min(timeit.repeat("BadHash('zz') in bad", globals=g, number=N))

    good_mem = sys.getsizeof(good)
    bad_mem = sys.getsizeof(bad)

    fig, (axl, axr) = plt.subplots(1, 2, figsize=(11.0, 5.0),
                                   gridspec_kw={"width_ratios": [2, 1]})
    labels = ["good_dict", "list scan", "bad_dict"]
    vals = [t_good, t_list, t_bad]
    cols = [COLORS["teal"], COLORS["amber"], COLORS["red"]]
    bars = axl.bar(labels, vals, color=cols, width=0.6)
    axl.bar_label(bars, labels=[f"{v:.3f}s\n({v / t_good:.0f}x)" for v in vals], padding=3, fontsize=9)
    axl.set_yscale("log")
    axl.set_ylabel(f"time for {N:,} 'zz' tests (s, log)")
    axl.set_title("ex06 - A bad hash collapses dict lookup")
    axl.annotate("bad hash even\nslower than a\nlist scan", xy=(2, t_bad), xytext=(0.35, t_bad * 0.32),
                 color=COLORS["red"], fontsize=10, fontweight="bold", ha="center",
                 arrowprops=dict(arrowstyle="->", color=COLORS["red"]))

    mbars = axr.bar(["good_set", "bad_set"], [good_mem, bad_mem],
                    color=[COLORS["teal"], COLORS["red"]], width=0.55)
    axr.bar_label(mbars, fmt="%d B", padding=3, fontsize=9)
    axr.set_ylabel("sys.getsizeof (bytes)")
    axr.set_title("Memory: identical")
    axr.set_ylim(0, max(good_mem, bad_mem) * 1.2)
    save(fig, __file__, name="chart.png",
         subtitle=f"Damage is all in TIME: same space, but bad hash -> O(n) probe chain (N reduced to 200k) | {CAP}")


if __name__ == "__main__":
    main()
