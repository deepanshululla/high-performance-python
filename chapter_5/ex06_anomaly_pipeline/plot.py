"""Visualize ex06: lazy anomaly pipeline -- time grows with n, memory stays flat.

Reuses the exercise's own first_n_anomaly_ranges and re-measures.

NOTE: ex06 is SLOW -- each anomaly takes ~one simulated week of seconds. Small
n values (2, 4, 6) are used here so the plot finishes quickly; the SHAPE (time
up, memory flat) matches the README, but the magnitudes are smaller than the
README's full-N numbers.

Run: .venv/bin/python chapter_5/ex06_anomaly_pipeline/plot.py
"""
import pathlib
import sys
from random import seed

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex06_anomaly_pipeline as ex  # noqa: E402  (sibling; its dir is sys.path[0])
from perf import time_s, peak_bytes  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402

CAP = "CPython 3.14 / macOS"
MB = 1024 * 1024


def main():
    setup()
    ns = [2, 4, 6]
    times, mems = [], []
    for n in ns:
        seed(0)
        t = time_s(lambda n=n: ex.first_n_anomaly_ranges(n), number=1, repeat=1)
        seed(0)
        m = peak_bytes(lambda n=n: ex.first_n_anomaly_ranges(n))
        times.append(t)
        mems.append(m / MB)

    fig, ax = plt.subplots(figsize=(8.8, 5.1))
    ax.plot(ns, times, "-o", color=COLORS["red"], lw=2, ms=7, label="time (s)")
    ax.set_xlabel("number of anomalies pulled")
    ax.set_ylabel("time (s)", color=COLORS["red"])
    ax.set_title("ex06 - lazy anomaly pipeline: time grows, memory flat")
    ax.set_xticks(ns)
    ax.legend(loc="upper left")

    ax2 = ax.twinx()
    ax2.plot(ns, mems, "-s", color=COLORS["teal"], lw=2, ms=7, label="peak mem (MB)")
    ax2.set_ylabel("peak memory (MB)", color=COLORS["teal"])
    ax2.set_ylim(0, max(mems) * 2.2)
    ax2.grid(False)
    ax2.spines["top"].set_visible(False)
    ax2.legend(loc="upper right")
    ax2.text(ns[len(ns) // 2], max(mems) * 1.25,
             "memory FLAT (~one day in flight);\nonly TIME grows with n",
             ha="center", color=COLORS["teal"], fontsize=9)
    save(fig, __file__,
         subtitle=f"islice stops the chain after the n-th anomaly: RAM is window-of-state, not dataset-size (n reduced to stay fast) | {CAP}",
         name="chart.png")


if __name__ == "__main__":
    main()
