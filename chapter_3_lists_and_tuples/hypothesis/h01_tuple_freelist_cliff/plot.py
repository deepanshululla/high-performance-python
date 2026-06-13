"""Visualize H1: the tuple freelist time-cliff at 20->21 vs the linear memory curve.

Run: .venv/bin/python chapter_3/hypothesis/h01_tuple_freelist_cliff/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import benchmark as B  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402


def main():
    setup()
    ns = list(range(0, 41))
    times = [B.time_build(n) for n in ns]
    sizes = [sys.getsizeof(tuple(range(n))) for n in ns]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.3))

    # Left: time, with the freelist boundary highlighted.
    ax1.axvspan(20.5, 40, color=COLORS["red"], alpha=0.06)
    ax1.axvline(20.5, color=COLORS["red"], ls="--", lw=1.3)
    ax1.plot(ns, times, "-o", color=COLORS["blue"], ms=4, lw=1.6)
    ax1.annotate("freelist ends\n(20 - 21): +16 ns step",
                 xy=(21, times[21]), xytext=(24, times[21] - 14),
                 color=COLORS["red"], fontsize=9.5,
                 arrowprops=dict(arrowstyle="->", color=COLORS["red"]))
    ax1.text(9, max(times) * 0.18, "freelist\n(sizes 1-20)", color=COLORS["blue"],
             fontsize=9.5, ha="center")
    ax1.set_title("Build time has a cliff at size 21")
    ax1.set_xlabel("tuple size n")
    ax1.set_ylabel("ns / build")

    # Right: memory, dead linear.
    ax2.axvline(20.5, color=COLORS["red"], ls="--", lw=1.3)
    ax2.plot(ns, sizes, "-o", color=COLORS["teal"], ms=4, lw=1.6)
    ax2.text(0.5, 0.9, "+8 B / element,\nstraight through 21\n(no memory cliff)",
             transform=ax2.transAxes, color=COLORS["teal"], fontsize=9.5, va="top")
    ax2.set_title("Memory is perfectly linear")
    ax2.set_xlabel("tuple size n")
    ax2.set_ylabel("getsizeof (bytes)")

    fig.suptitle("H1 - Tuple freelist: a TIME cliff at 20 - 21, no MEMORY cliff",
                 fontsize=13, fontweight="bold")
    save(fig, __file__,
         subtitle="CONFIRMED - allocation effect (freelist), not a size effect | CPython 3.14 / macOS")


if __name__ == "__main__":
    main()
