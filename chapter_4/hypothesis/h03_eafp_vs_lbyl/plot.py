"""Visualize H3: the best dict-access idiom flips with the hit rate (crossover).

Run: .venv/bin/python chapter_4/hypothesis/h03_eafp_vs_lbyl/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import benchmark as B  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402


def main():
    setup()
    d = {i: i for i in range(B.SIZE)}
    rates = [1.0, 0.99, 0.9, 0.7, 0.5, 0.3, 0.1, 0.0]
    lbyl, get, eafp = [], [], []
    for hr in rates:
        keys = B.make_probes(hr)
        lbyl.append(B.time_idiom(B.LBYL, keys, d))
        get.append(B.time_idiom(B.GET, keys, d))
        eafp.append(B.time_idiom(B.EAFP, keys, d))

    xs = [hr * 100 for hr in rates]
    fig, ax = plt.subplots(figsize=(8.6, 5.1))
    ax.plot(xs, lbyl, "-o", color=COLORS["blue"], lw=1.9, ms=5, label="LBYL  (in + [])")
    ax.plot(xs, get, "-o", color=COLORS["teal"], lw=1.9, ms=5, label="get()")
    ax.plot(xs, eafp, "-o", color=COLORS["red"], lw=1.9, ms=5, label="EAFP  (try/except)")

    ax.annotate("EAFP wins\n(one lookup,\nno exception)", xy=(100, eafp[0]),
                xytext=(78, eafp[0] - 30), color=COLORS["red"], fontsize=9.5,
                arrowprops=dict(arrowstyle="->", color=COLORS["red"]))
    ax.annotate("EAFP worst\n(exception tax)", xy=(0, eafp[-1]),
                xytext=(8, eafp[-1] - 18), color=COLORS["red"], fontsize=9.5,
                arrowprops=dict(arrowstyle="->", color=COLORS["red"]))

    ax.set_xlabel("hit rate (% of probes present)")
    ax.set_ylabel("ns / access")
    ax.set_title("H3 - Dict-access idioms cross over with hit rate")
    ax.legend(loc="upper center")
    save(fig, __file__,
         subtitle="CONFIRMED - EAFP -> get -> LBYL as keys go from usually-present to usually-absent | CPython 3.14 / macOS")


if __name__ == "__main__":
    main()
