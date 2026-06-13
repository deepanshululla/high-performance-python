"""Visualize ex07: rolling window -- copying to a tuple erases the deque's advantage.

Reuses the exercise's own groupby_window_* implementations and re-measures.

NOTE: ex07 is SLOW at 50k items x big windows. The stream is reduced to 10k
here so the plot finishes quickly; the SHAPE (deque+copy NOT faster than
tuple-rebuild; only deque-in-place flat) matches the README.

Run: .venv/bin/python chapter_5/ex07_rolling_window/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex07_rolling_window as ex  # noqa: E402  (sibling; its dir is sys.path[0])
from perf import time_s  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402

CAP = "CPython 3.14 / macOS"


def main():
    setup()
    stream = list(range(10_000))
    windows = [100, 1_000, 5_000]
    t_tup, t_cpy, t_inp = [], [], []
    for w in windows:
        t_tup.append(time_s(lambda w=w: sum(len(x) for x in ex.groupby_window_tuple(stream, w)), number=1, repeat=2) * 1e3)
        t_cpy.append(time_s(lambda w=w: sum(len(x) for x in ex.groupby_window_deque(stream, w)), number=1, repeat=2) * 1e3)
        t_inp.append(time_s(lambda w=w: sum(len(x) for x in ex.groupby_window_deque_inplace(stream, w)), number=1, repeat=2) * 1e3)

    import numpy as np
    x = np.arange(len(windows))
    bw = 0.26
    fig, ax = plt.subplots(figsize=(9.4, 5.3))
    b1 = ax.bar(x - bw, t_tup, bw, label="tuple-rebuild", color=COLORS["amber"])
    b2 = ax.bar(x, t_cpy, bw, label="deque + copy", color=COLORS["red"])
    b3 = ax.bar(x + bw, t_inp, bw, label="deque in-place", color=COLORS["teal"])
    for b in (b1, b2, b3):
        ax.bar_label(b, fmt="%.1f", padding=2, fontsize=8)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([f"window={w}" for w in windows])
    ax.set_ylabel("time (ms, log)")
    ax.set_title("ex07 - rolling window: copy erases the deque's advantage")
    ax.legend(loc="upper left")
    save(fig, __file__,
         subtitle=f"Counterintuitive: deque+copy is NOT faster than tuple-rebuild; only deque-in-place stays flat (stream reduced) | {CAP}",
         name="chart.png")


if __name__ == "__main__":
    main()
