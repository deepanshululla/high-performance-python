"""Visualize ex03: the len([...]) trap -- equal time, huge memory gap.

Reuses the exercise's own count_with_list / count_with_gen and re-measures.

Run: .venv/bin/python chapter_5/ex03_len_trap/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex03_len_trap as ex  # noqa: E402  (sibling; its dir is sys.path[0])
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
    t_list = time_s(ex.count_with_list, number=1, repeat=3) * 1e3
    t_gen = time_s(ex.count_with_gen, number=1, repeat=3) * 1e3
    m_list = peak_bytes(ex.count_with_list)
    m_gen = peak_bytes(ex.count_with_gen)

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(10.4, 5.0))
    _bar_time(axL, ["len([ ... ])", "sum(1 for ... )"], [t_list, t_gen],
              [COLORS["amber"], COLORS["teal"]], "time (ms)",
              "ex03 - count divisible-by-3: time (= equal)")
    _bar_log_mem(axR, ["len([ ... ])", "sum(1 for ... )"], [m_list, m_gen],
                 [COLORS["amber"], COLORS["teal"]],
                 "ex03 - the len([]) trap: memory")
    axR.text(0.5, m_list * 0.5, "only [] vs ()\nin the source",
             ha="center", fontsize=9, color=COLORS["gray"])
    save(fig, __file__,
         subtitle=f"Same time, same answer - [] materializes every match, () folds one at a time | {CAP}",
         name="chart.png")


if __name__ == "__main__":
    main()
