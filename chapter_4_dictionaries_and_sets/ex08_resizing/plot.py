"""Visualize ex08: power-of-two size classes + amortized O(1) inserts.

Run: .venv/bin/python chapter_4/ex08_resizing/plot.py
"""
import pathlib
import sys

from matplotlib.ticker import ScalarFormatter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex08_resizing as ex  # noqa: E402
from perf import time_s  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402

CAP = "CPython 3.14 / macOS"


def main():
    setup()
    # left: capacity (table size) vs N using the exercise's table_size_for()
    Ns = list(range(1, 1200))
    caps = [ex.table_size_for(n) for n in Ns]

    # right: ns/insert for 100k vs 1M dict build (reduced repeats, shape = flat)
    def build(n):
        out = {}
        for i in range(n):
            out[i] = i
        return out

    per = []
    for n in (100_000, 1_000_000):
        per.append(time_s(lambda: build(n), number=1, repeat=3) / n * 1e9)

    fig, (axl, axr) = plt.subplots(1, 2, figsize=(11.0, 5.0))
    axl.step(Ns, caps, where="post", color=COLORS["violet"], lw=2)
    axl.set_yscale("log", base=2)
    axl.set_xlabel("N items inserted")
    axl.set_ylabel("table capacity (buckets, log2)")
    axl.set_title("ex08 - Power-of-two size classes")
    axl.set_yticks([8, 16, 32, 64, 128, 256, 512, 1024, 2048])
    axl.get_yaxis().set_major_formatter(ScalarFormatter())

    bars = axr.bar(["100k-key", "1M-key"], per,
                   color=[COLORS["blue"], COLORS["teal"]], width=0.55)
    axr.bar_label(bars, fmt="%.1f ns", padding=3, fontsize=11)
    axr.set_ylabel("ns / insert")
    axr.set_title("Amortized O(1) inserts")
    axr.set_ylim(0, max(per) * 1.3)
    save(fig, __file__, name="chart.png",
         subtitle=f"Rare O(n) resizes at each 2^k boundary amortize to a flat ns/insert | {CAP}")


if __name__ == "__main__":
    main()
