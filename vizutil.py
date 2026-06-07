"""Shared matplotlib styling for the hypothesis visualizations.

Each chapter_*/hypothesis/<name>/plot.py imports this, reuses the measurement
functions from its sibling benchmark.py, and saves a chart.png next to itself:

    import pathlib, sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
    from vizutil import plt, setup, save, COLORS
    setup()
    fig, ax = plt.subplots(...)
    ...
    save(fig, __file__, subtitle="VERDICT: CONFIRMED -- ...")
"""
import pathlib

import matplotlib

matplotlib.use("Agg")  # headless: render straight to PNG, no display needed
import matplotlib.pyplot as plt  # noqa: E402

INK = "#1b1b2b"
COLORS = {
    "blue": "#2563eb",
    "teal": "#0d9488",
    "red": "#dc2626",
    "amber": "#d97706",
    "violet": "#7c3aed",
    "gray": "#9ca3af",
    "grid": "#e6e8ec",
}


def setup():
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#c8ccd2",
        "axes.labelcolor": INK,
        "axes.titlecolor": INK,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": COLORS["grid"],
        "grid.linewidth": 0.9,
        "xtick.color": INK,
        "ytick.color": INK,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.frameon": False,
        "legend.fontsize": 10,
        "font.family": "sans-serif",
        "font.size": 11,
        "figure.dpi": 130,
    })


def despine(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def save(fig, file_dunder, subtitle=None, name="chart.png"):
    """Tight-layout, stamp an optional verdict caption, write chart.png alongside file_dunder."""
    for ax in fig.get_axes():
        despine(ax)
    if subtitle:
        fig.text(0.5, 0.005, subtitle, ha="center", va="bottom",
                 fontsize=9.5, color="#444", style="italic")
        fig.tight_layout(rect=(0, 0.045, 1, 1))
    else:
        fig.tight_layout()
    out = pathlib.Path(file_dunder).resolve().parent / name
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {out}")
    return out
