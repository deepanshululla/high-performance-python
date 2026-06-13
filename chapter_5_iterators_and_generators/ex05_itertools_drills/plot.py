"""Visualize ex05: lazy sum(islice(count())) vs eager sum(list(range)) -- time + memory.

Mirrors the exercise's own lazy/eager comparison over the first 1M ints.

Run: .venv/bin/python chapter_5/ex05_itertools_drills/plot.py
"""
import pathlib
import sys
from itertools import islice, count

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex05_itertools_drills as ex  # noqa: E402, F401  (sibling; its dir is sys.path[0])
from perf import time_s, peak_bytes  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402

CAP = "CPython 3.14 / macOS"


def _human(n):
    n = float(n)
    for u in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"


def _bar_time(ax, labels, vals, colors, ylabel, title, fmt="%.1f"):
    bars = ax.bar(labels, vals, color=colors, width=0.55)
    ax.bar_label(bars, fmt=fmt, padding=3, fontsize=9.5)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_ylim(0, max(vals) * 1.25)


def _bar_log_mem(ax, labels, vals_bytes, colors, title):
    bars = ax.bar(labels, vals_bytes, color=colors, width=0.55)
    ax.set_yscale("log")
    ax.bar_label(bars, labels=[_human(v) for v in vals_bytes], padding=3, fontsize=9.5)
    ax.set_ylabel("peak memory (bytes, log)")
    ax.set_title(title)
    ax.set_ylim(min(vals_bytes) * 0.3, max(vals_bytes) * 6)


def main():
    setup()
    N = 1_000_000
    lazy = lambda: sum(islice(count(), N))
    eager = lambda: sum(list(range(N)))
    t_lazy = time_s(lazy, number=3) * 1e3
    t_eager = time_s(eager, number=3) * 1e3
    m_lazy = peak_bytes(lazy)
    m_eager = peak_bytes(eager)

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(10.4, 5.0))
    _bar_time(axL, ["lazy\nsum(islice)", "eager\nsum(list)"], [t_lazy, t_eager],
              [COLORS["teal"], COLORS["red"]], "time (ms)",
              "ex05 - sum first 1,000,000 ints: time")
    _bar_log_mem(axR, ["lazy\nsum(islice)", "eager\nsum(list)"], [m_lazy, m_eager],
                 [COLORS["teal"], COLORS["red"]],
                 "ex05 - itertools stays O(1): memory")
    save(fig, __file__,
         subtitle=f"itertools composition is O(1) RAM and often faster - eager list pays O(n) memory | {CAP}",
         name="chart.png")


if __name__ == "__main__":
    main()
