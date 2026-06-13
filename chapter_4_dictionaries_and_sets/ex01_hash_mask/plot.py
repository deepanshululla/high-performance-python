"""Visualize ex01: masking keeps only low bits, so first-letters collide.

Run: .venv/bin/python chapter_4/ex01_hash_mask/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex01_hash_mask as ex  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402

CAP = "CPython 3.14 / macOS"


def main():
    setup()
    # pick cities whose first letters spread across buckets, with Rome & Barcelona
    # deliberately colliding (ord 'R'=82 & 7 = 2, 'B'=66 & 7 = 2).
    cities = ["Athens", "Barcelona", "Rome", "Cairo", "Dublin",
              "Madrid", "Naples", "Oslo", "Paris"]
    by_bucket = {b: [] for b in range(8)}
    for c in cities:
        by_bucket[ex.bucket(ord(c[0]), 8)].append(c)

    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    for b in range(8):
        names = by_bucket[b]
        collide = len(names) > 1
        for level, c in enumerate(names):
            highlight = collide and c in ("Rome", "Barcelona")
            color = COLORS["red"] if collide else COLORS["teal"]
            ax.add_patch(plt.Rectangle((b - 0.42, level + 0.12), 0.84, 0.74,
                                       color=color, ec="white", lw=2, zorder=3))
            ax.text(b, level + 0.49, c, ha="center", va="center", fontsize=9,
                    color="white", zorder=4, fontweight="bold")
            if highlight:
                ax.add_patch(plt.Rectangle((b - 0.42, level + 0.12), 0.84, 0.74,
                                           fill=False, ec="#1b1b2b", lw=2, ls="--", zorder=5))
    for b, names in by_bucket.items():
        if len(names) > 1:
            top = len(names)
            ax.annotate("collision\n(Rome & Barcelona)", xy=(b, top - 0.1),
                        xytext=(b, top + 1.0), ha="center", color=COLORS["red"],
                        fontsize=10, fontweight="bold",
                        arrowprops=dict(arrowstyle="->", color=COLORS["red"]))
    ax.set_xticks(range(8))
    ax.set_xticklabels([f"{b}\n0b{b:03b}" for b in range(8)])
    ax.set_yticks([])
    ax.set_xlim(-0.6, 7.6)
    ax.set_ylim(-0.1, max(len(v) for v in by_bucket.values()) + 1.6)
    ax.set_xlabel("bucket = ord(name[0]) & 0b111")
    ax.set_title("ex01 - Masking keeps only low bits, so first-letters collide")
    save(fig, __file__, name="chart.png",
         subtitle=f"Rome & Barcelona share bucket 2: ord('R')-ord('B')=16=2^4, identical low 3 bits | {CAP}")


if __name__ == "__main__":
    main()
