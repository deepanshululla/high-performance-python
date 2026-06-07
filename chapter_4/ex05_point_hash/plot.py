"""Visualize ex05: content hashing lets a set deduplicate value-equal points.

Run: .venv/bin/python chapter_4/ex05_point_hash/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex05_point_hash as ex  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402

CAP = "CPython 3.14 / macOS"


def main():
    setup()
    a, b = ex.PointDefault(1, 1), ex.PointDefault(1, 1)
    default_size = len({a, b})  # 2: id-hash, no dedup
    p1, p2 = ex.Point(1, 1), ex.Point(1, 1)
    content_size = len({p1, p2})  # 1: deduped

    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    bars = ax.bar(["default\n(id-hash)", "content\n__hash__/__eq__"],
                  [default_size, content_size],
                  color=[COLORS["gray"], COLORS["teal"]], width=0.55)
    ax.bar_label(bars, labels=[f"{default_size} elems\n(no dedup)", f"{content_size} elem\n(deduped)"],
                 padding=4, fontsize=10)
    ax.set_ylabel("len(set) for two Point(1,1)")
    ax.set_ylim(0, 2.6)
    ax.set_yticks([0, 1, 2])
    ax.set_title("ex05 - Content hashing lets a set deduplicate value-equal points")
    save(fig, __file__, name="chart.png",
         subtitle=f"hash=(x,y) + __eq__ collapses two equal points into one set member | {CAP}")


if __name__ == "__main__":
    main()
