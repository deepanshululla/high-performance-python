"""Visualize ex09: the mask, not the int hash, creates collisions.

Run: .venv/bin/python chapter_4/ex09_int_hash/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex09_int_hash as ex  # noqa: E402,F401  (sibling module; imported for symmetry)
from vizutil import plt, setup, save, COLORS  # noqa: E402

CAP = "CPython 3.14 / macOS"


def main():
    setup()
    fig, (axl, axr) = plt.subplots(1, 2, figsize=(10.5, 4.6))
    for ax, size, title in [(axl, 8, "mask 0b111 (8 buckets)"),
                            (axr, 1024, "mask 0b11_1111_1111 (1024 buckets)")]:
        mask = size - 1
        a, b = 5 & mask, 501 & mask
        collide = a == b
        bars = ax.bar(["5", "501"], [a, b],
                      color=[COLORS["red"] if collide else COLORS["teal"]] * 2, width=0.5)
        ax.bar_label(bars, labels=[f"-> {a}", f"-> {b}"], padding=3, fontsize=11)
        verdict = "COLLIDE" if collide else "distinct -> ok"
        ax.set_title(f"{title}\n{verdict}",
                     color=COLORS["red"] if collide else COLORS["teal"])
        ax.set_ylabel("bucket index")
        ax.set_ylim(0, max(a, b, 10) * 1.2)
    fig.suptitle("ex09 - The mask, not the int hash, creates collisions",
                 fontsize=13, fontweight="bold", color="#1b1b2b")
    save(fig, __file__, name="chart.png",
         subtitle=f"hash(int)==int, so 5 & 501 collide only when the mask drops their distinguishing bits | {CAP}")


if __name__ == "__main__":
    main()
