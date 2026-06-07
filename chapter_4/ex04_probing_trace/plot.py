"""Visualize ex04: open addressing -- teal=occupied, amber=tombstone, gray=empty.

Run: .venv/bin/python chapter_4/ex04_probing_trace/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import ex04_probing_trace as ex  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402

CAP = "CPython 3.14 / macOS"


def main():
    setup()
    # reuse the exercise's TinyDict + probe logic to build the real slots state
    d = ex.TinyDict(8)
    for city, country in [("Rome", "Italy"), ("San Francisco", "USA"),
                          ("New York", "USA"), ("Barcelona", "Spain")]:
        d.insert(city, country)
    d.delete("Rome")  # leaves a tombstone
    slots = d.slots

    fig, ax = plt.subplots(figsize=(11.0, 3.2))
    for i, slot in enumerate(slots):
        if slot is None:
            color, label, txtcol = COLORS["grid"], "(empty)", "#888"
        elif slot is ex.TOMBSTONE:
            color, label, txtcol = COLORS["amber"], ex.TOMBSTONE, "white"
        elif isinstance(slot, tuple):
            color, label, txtcol = COLORS["teal"], str(slot[0]), "white"
        else:
            color, label, txtcol = COLORS["grid"], str(slot), "#888"
        ax.add_patch(plt.Rectangle((i, 0), 0.92, 1, color=color, ec="white", lw=2))
        ax.text(i + 0.46, 0.5, label, ha="center", va="center",
                fontsize=9, color=txtcol, fontweight="bold")
        ax.text(i + 0.46, -0.22, str(i), ha="center", va="center", fontsize=9, color="#444")
    ax.set_xlim(-0.1, 8.1)
    ax.set_ylim(-0.45, 1.15)
    ax.axis("off")
    ax.set_title("ex04 - Open addressing: teal=occupied, amber=tombstone, gray=empty",
                 color="#1b1b2b", fontweight="bold", fontsize=13)
    save(fig, __file__, name="chart.png",
         subtitle=f"Deleting Rome leaves a tombstone, not NULL, so Barcelona's probe chain survives | {CAP}")


if __name__ == "__main__":
    main()
