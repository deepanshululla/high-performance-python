"""Visualize H1: the dict-insert resize "sawtooth" hidden behind the amortized mean.

Run: .venv/bin/python chapter_4/hypothesis/h01_insert_sawtooth/plot.py
"""
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from vizutil import plt, setup, save, COLORS  # noqa: E402

N = 1_000_000


def measure():
    d = {}
    times = [0] * N
    resizes = []
    prev = sys.getsizeof(d)
    pc = time.perf_counter_ns
    for i in range(N):
        t0 = pc()
        d[i] = i
        t1 = pc()
        times[i] = t1 - t0
        s = sys.getsizeof(d)
        if s != prev:
            resizes.append((i, t1 - t0))
            prev = s
    return times, resizes


def main():
    setup()
    times, resizes = measure()
    median = sorted(times)[N // 2]
    mean = sum(times) / N

    # Downsample the cloud of normal inserts so the PNG stays light.
    step = 400
    xs = list(range(1, N, step))
    ys = [max(times[i], 1) / 1000 for i in xs]  # us, floor at 1ns to keep log happy
    rx = [i + 1 for i, _ in resizes]
    ry = [t / 1000 for _, t in resizes]

    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    ax.scatter(xs, ys, s=3, color=COLORS["gray"], alpha=0.35, rasterized=True,
               label="individual inserts (sampled)")
    ax.plot(rx, ry, "-o", color=COLORS["red"], ms=6, lw=1.6,
            label="resize inserts (full rehash)")
    ax.axhline(median / 1000, color=COLORS["blue"], ls="--", lw=1.2,
               label=f"median insert ({median} ns)")
    ax.axhline(mean / 1000, color=COLORS["teal"], ls=":", lw=1.4,
               label=f"amortized mean ({mean:.0f} ns ~ ex08)")

    last_i, last_t = resizes[-1]
    ax.annotate(f"last resize copies ~{last_i//1000}k keys:\n{last_t/1000:.0f} us = {last_t/median:.0f}x a normal insert",
                xy=(last_i, last_t / 1000), xytext=(last_i * 0.05, last_t / 1000 * 0.6),
                color=COLORS["red"], fontsize=9.5,
                arrowprops=dict(arrowstyle="->", color=COLORS["red"]))

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("insert number")
    ax.set_ylabel("insert time (microseconds)")
    ax.set_title("H1 - Dict inserts: an O(n) resize sawtooth under a flat amortized mean")
    ax.legend(loc="upper left")
    save(fig, __file__,
         subtitle=f"CONFIRMED - {len(resizes)} resize spikes at doubling boundaries, growing with N | CPython 3.14 / macOS")


if __name__ == "__main__":
    main()
