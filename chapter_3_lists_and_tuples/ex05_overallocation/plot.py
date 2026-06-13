"""Visualize ex05: list overallocation headroom jumps + append vs list() build.

Reuses ex05's capacity_from_size. Sizes are reduced from the README to keep
runtime reasonable -- the SHAPE/ordering is the point, so exact magnitudes will
differ from the README numbers.

Run: .venv/bin/python chapter_3/ex05_overallocation/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex05_overallocation as ex  # noqa: E402
from perf import time_s  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402

CPU = "CPython 3.14 / macOS"
NOTE = "exact magnitudes differ from the README (yours will differ)"


def main():
    setup()
    # Left: capacity vs len while appending (watch getsizeof growth).
    lens, caps = [], []
    l = []
    for i in range(40):
        l.append(i)
        lens.append(len(l))
        caps.append(ex.capacity_from_size(sys.getsizeof(l)))

    # Right: append-loop vs list(range) build time (README uses 1e6).
    def build_append():
        out = []
        for i in range(200_000):
            out.append(i)
        return out

    t_app = time_s(build_append, number=1, repeat=3) * 1e3
    t_list = time_s(lambda: list(range(200_000)), number=1, repeat=3) * 1e3

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6))

    ax1.step(lens, caps, where="post", color=COLORS["blue"], lw=1.8)
    ax1.plot(lens, lens, color=COLORS["gray"], lw=1.2, ls="--", label="len (no headroom)")
    ax1.plot(lens, caps, "o", color=COLORS["blue"], ms=3.5, label="capacity")
    ax1.set_title("Overallocation: capacity jumps ahead of len")
    ax1.set_xlabel("len (number of appends)")
    ax1.set_ylabel("capacity (slots)")
    ax1.legend()

    bars = ax2.bar(["append loop", "list(range)"], [t_app, t_list],
                   color=[COLORS["red"], COLORS["teal"]], width=0.55)
    ax2.set_ylabel("build time (ms)")
    ax2.set_title("Build time: list() skips repeated resize+copy")
    ax2.bar_label(bars, fmt="%.1f ms", padding=3, fontsize=10)
    ax2.annotate(f"~{t_app / t_list:.1f}x faster",
                 xy=(1, t_list), xytext=(0.5, (t_app + t_list) / 2),
                 ha="center", color=COLORS["violet"], fontsize=10, fontweight="bold")

    fig.suptitle("ex05 - List overallocation: headroom jumps + build cost",
                 fontsize=13, fontweight="bold")
    save(fig, __file__, name="chart.png",
         subtitle=f"capacity overshoots len in geometric steps; list() allocates exactly once | {NOTE} | {CPU}")


if __name__ == "__main__":
    main()
