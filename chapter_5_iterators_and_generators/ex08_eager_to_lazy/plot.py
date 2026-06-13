"""Visualize ex08: eager load-all vs lazy stop-early -- first match in 1M+ lines.

Reuses the exercise's own find_matches_eager / find_matches_lazy and re-measures.

Run: .venv/bin/python chapter_5/ex08_eager_to_lazy/plot.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex08_eager_to_lazy as ex  # noqa: E402  (sibling; its dir is sys.path[0])
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
    big = pathlib.Path(tempfile.gettempdir()) / "ch5_ex08_plot_big.log"
    with open(big, "w") as f:
        f.write("ERROR right at the top\n")
        for i in range(1_000_000):
            f.write(f"line {i} all good\n")

    eager_first = lambda: ex.find_matches_eager(str(big), "ERROR")[0]
    lazy_first = lambda: next(ex.find_matches_lazy(str(big), "ERROR"))
    t_eager = time_s(eager_first, number=1, repeat=3) * 1e3
    t_lazy = time_s(lazy_first, number=1, repeat=3) * 1e3
    m_eager = peak_bytes(eager_first)
    m_lazy = peak_bytes(lazy_first)
    big.unlink()

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(10.4, 5.0))
    _bar_time(axL, ["eager\n(load all)", "lazy\n(stop early)"], [t_eager, t_lazy],
              [COLORS["red"], COLORS["teal"]], "time (ms)",
              "ex08 - first match in 1,000,001 lines: time")
    _bar_log_mem(axR, ["eager\n(load all)", "lazy\n(stop early)"], [m_eager, m_lazy],
                 [COLORS["red"], COLORS["teal"]],
                 "ex08 - eager vs lazy pipeline: memory")
    save(fig, __file__,
         subtitle=f"Lazy reads ~one line near the top; eager reads + stores all 1M lines first | {CAP}",
         name="chart.png")


if __name__ == "__main__":
    main()
