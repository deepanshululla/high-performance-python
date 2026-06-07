"""Visualize H5: __slots__ shrinks the ex05 Point (memory), behavior unchanged.

Run: .venv/bin/python chapter_4/hypothesis/h05_slots_memory/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import benchmark as B  # noqa: E402
from perf import peak_bytes  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402


def main():
    setup()
    peak_dict = peak_bytes(lambda: B.build(B.PointDict)) / 1e6
    peak_slots = peak_bytes(lambda: B.build(B.PointSlots)) / 1e6

    fig, ax = plt.subplots(figsize=(7.2, 5))
    labels = ["PointDict\n(per-instance __dict__)", "PointSlots\n(__slots__)"]
    vals = [peak_dict, peak_slots]
    bars = ax.bar(labels, vals, color=[COLORS["red"], COLORS["teal"]], width=0.55)
    ax.bar_label(bars, fmt="%.1f MB", padding=3, fontsize=11)

    saved = peak_dict - peak_slots
    ax.annotate(f"-{saved:.0f} MB  ({saved*1e6/B.N:.0f} B/instance)\n{peak_dict/peak_slots:.2f}x smaller",
                xy=(1, peak_slots), xytext=(0.55, peak_dict * 0.72),
                color=COLORS["teal"], fontsize=10.5, ha="center",
                arrowprops=dict(arrowstyle="->", color=COLORS["teal"]))
    ax.set_ylabel("peak heap (MB)")
    ax.set_ylim(0, peak_dict * 1.18)
    ax.set_title(f"H5 - __slots__ on a content-hashed Point ({B.N:,} instances)")
    save(fig, __file__,
         subtitle="CONFIRMED - 1.45x less memory, identical dedup/membership (no __dict__) | CPython 3.14 / macOS")


if __name__ == "__main__":
    main()
