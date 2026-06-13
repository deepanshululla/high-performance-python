"""Visualize ex01: same 1M-item loop, list vs generator -- time near-equal, memory chasm.

Reuses the exercise's own `gen` and re-measures with perf.time_s / perf.peak_bytes.

NOTE: N is full-size here; the SHAPE/ordering of the bars matches the README.

Run: .venv/bin/python chapter_5/ex01_for_deconstructed/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex01_for_deconstructed as ex  # noqa: E402  (sibling; its dir is sys.path[0])
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
    consume_list = lambda: sum(1 for _ in list(range(N)))
    consume_gen = lambda: sum(1 for _ in ex.gen(N))

    t_list = time_s(consume_list, number=3) * 1e3
    t_gen = time_s(consume_gen, number=3) * 1e3
    m_list = peak_bytes(consume_list)
    m_gen = peak_bytes(consume_gen)

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(10.4, 5.0))
    _bar_time(axL, ["prebuilt\nlist", "generator"], [t_list, t_gen],
              [COLORS["red"], COLORS["teal"]], "loop time (ms)",
              "ex01 - loop over 1,000,000 items: time")
    _bar_log_mem(axR, ["prebuilt\nlist", "generator"], [m_list, m_gen],
                 [COLORS["red"], COLORS["teal"]],
                 "ex01 - peak memory: list vs generator")
    axR.annotate("memory chasm:\nlist stores all N,\ngen holds O(1) state",
                 xy=(1, m_gen), xytext=(0.30, m_list * 0.04),
                 fontsize=9, color=COLORS["teal"])
    save(fig, __file__,
         subtitle=f"List materializes all N; the generator stays O(1) - same loop, ~{m_list / max(m_gen, 1):,.0f}x less RAM | {CAP}",
         name="chart.png")


if __name__ == "__main__":
    main()
