"""Visualize ex02: Fibonacci list vs generator -- the headline memory win.

Reuses the exercise's own consume_list / consume_gen and re-measures.

NOTE: ex02 builds 100k big ints (heavy in memory). The SHAPE/ordering of the
bars matches the README; exact magnitudes may differ from the full-N numbers.

Run: .venv/bin/python chapter_5/ex02_fib_list_vs_gen/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex02_fib_list_vs_gen as ex  # noqa: E402  (sibling; its dir is sys.path[0])
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
    t_list = time_s(ex.consume_list, number=1, repeat=3) * 1e3
    t_gen = time_s(ex.consume_gen, number=1, repeat=3) * 1e3
    m_list = peak_bytes(ex.consume_list)
    m_gen = peak_bytes(ex.consume_gen)
    ratio = m_list / max(m_gen, 1)

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(10.4, 5.0))
    _bar_time(axL, ["fibonacci\nlist", "fibonacci\ngen"], [t_list, t_gen],
              [COLORS["red"], COLORS["teal"]], "time (ms)",
              "ex02 - Fibonacci 100,000: time")
    _bar_log_mem(axR, ["fibonacci\nlist", "fibonacci\ngen"], [m_list, m_gen],
                 [COLORS["red"], COLORS["teal"]],
                 "ex02 - Fibonacci: list vs generator memory")
    axR.annotate(f"~{ratio:,.0f}x\nless memory",
                 xy=(1, m_gen), xytext=(0.55, m_list * 0.02),
                 fontsize=10, color=COLORS["teal"], fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color=COLORS["teal"]))
    save(fig, __file__,
         subtitle=f"Generator never materializes the sequence: thousands-x less RAM (list stores 100k big ints) | {CAP}",
         name="chart.png")


if __name__ == "__main__":
    main()
