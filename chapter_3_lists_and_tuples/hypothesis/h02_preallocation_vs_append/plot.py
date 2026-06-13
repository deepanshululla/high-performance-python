"""Visualize H2: preallocation vs append-growth (build time + dead headroom).

Run: .venv/bin/python chapter_3/hypothesis/h02_preallocation_vs_append/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import benchmark as B  # noqa: E402
from perf import time_s  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402


def main():
    setup()
    labels = ["append\nloop", "[None]*N\n+ assign", "list(range(N))"]
    fns = [B.build_append, B.build_prealloc, B.build_listrange]
    times = [time_s(fn, number=1, repeat=5) * 1e3 for fn in fns]
    sizes = [sys.getsizeof(fn()) / 1e6 for fn in fns]
    bar_colors = [COLORS["red"], COLORS["amber"], COLORS["teal"]]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.3))

    b1 = ax1.bar(labels, times, color=bar_colors, width=0.62)
    ax1.bar_label(b1, fmt="%.1f ms", padding=3, fontsize=10)
    ax1.set_title(f"Build time  (append is {times[0]/times[2]:.2f}x slower than list(range))")
    ax1.set_ylabel("milliseconds")
    ax1.set_ylim(0, max(times) * 1.2)

    b2 = ax2.bar(labels, sizes, color=bar_colors, width=0.62)
    ax2.bar_label(b2, fmt="%.1f MB", padding=3, fontsize=10)
    ax2.axhline(sizes[2], color=COLORS["gray"], ls="--", lw=1)
    ax2.annotate("append carries\ndead headroom",
                 xy=(0, sizes[0]), xytext=(0.45, sizes[0] + 0.18),
                 color=COLORS["red"], fontsize=9.5,
                 arrowprops=dict(arrowstyle="->", color=COLORS["red"]))
    ax2.set_title("Result size  (exact-alloc methods are tighter)")
    ax2.set_ylabel("megabytes")
    ax2.set_ylim(0, max(sizes) * 1.18)

    fig.suptitle("H2 - Preallocate, don't append-grow: faster build AND no headroom",
                 fontsize=13, fontweight="bold")
    save(fig, __file__,
         subtitle="CONFIRMED - the cleanest win is memory; list(range) wins on speed | CPython 3.14 / macOS")


if __name__ == "__main__":
    main()
