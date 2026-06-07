"""Visualize ex09: sum(map(...)) vs sum(list(map(...))) -- O(1) vs O(n) memory.

Mirrors the exercise's own lazy/eager memory comparison over range(1M).

Run: .venv/bin/python chapter_5/ex09_lazy_builtins/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex09_lazy_builtins as ex  # noqa: E402, F401  (sibling; its dir is sys.path[0])
from perf import peak_bytes  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402

CAP = "CPython 3.14 / macOS"


def _human(n):
    n = float(n)
    for u in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"


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
    lazy = lambda: sum(map(lambda x: x * 2, range(N)))
    eager = lambda: sum(list(map(lambda x: x * 2, range(N))))
    m_lazy = peak_bytes(lazy)
    m_eager = peak_bytes(eager)

    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    _bar_log_mem(ax, ["sum(map(...))", "sum(list(map(...)))"], [m_lazy, m_eager],
                 [COLORS["teal"], COLORS["red"]],
                 "ex09 - lazy vs eager built-in: memory (sum 2.x over 1,000,000)")
    ax.text(0.5, m_eager * 0.04,
            "LAZY  : map / zip / filter / reversed /\n         enumerate / range / dict.items\nEAGER : sorted / list",
            ha="center", fontsize=9, color=COLORS["gray"],
            bbox=dict(boxstyle="round", fc="white", ec=COLORS["grid"]))
    save(fig, __file__,
         subtitle=f"Wrapping a lazy iterator in list() throws away the streaming win - O(1) becomes O(n) | {CAP}",
         name="chart.png")


if __name__ == "__main__":
    main()
