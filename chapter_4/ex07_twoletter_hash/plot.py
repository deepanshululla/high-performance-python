"""Visualize ex07: an 'ideal' hash is relative to table size.

Run: .venv/bin/python chapter_4/ex07_twoletter_hash/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex07_twoletter_hash as ex  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402

CAP = "CPython 3.14 / macOS"


def main():
    setup()
    sizes = [2048, 1024, 512]
    cols = [ex.collisions(s) for s in sizes]

    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    bars = ax.bar([str(s) for s in sizes], cols,
                  color=[COLORS["teal"], COLORS["teal"], COLORS["red"]], width=0.55)
    ax.bar_label(bars, fmt="%d", padding=3, fontsize=11)
    ax.set_xlabel("table size (buckets)")
    ax.set_ylabel("collisions among 676 two-letter keys")
    ax.set_title("ex07 - 'Ideal' hash is relative to table size")
    ax.set_ylim(0, max(cols) * 1.25 + 10)
    save(fig, __file__, name="chart.png",
         subtitle=f"Perfect at 2048/1024 (max value 675 < mask), but wraps into 164 collisions at 512 | {CAP}")


if __name__ == "__main__":
    main()
