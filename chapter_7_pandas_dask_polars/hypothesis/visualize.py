"""Tile every Chapter 7 hypothesis chart into a single dashboard.

Each hypothesis folder has its own `bench.py --plot` that saves its chart PNG. This driver
just assembles those PNGs into `hypothesis_dashboard.png` -- it does NOT re-run the benchmarks
(some, like H2's Dask sweep and H3's Parquet scan, are slow). Regenerate an individual chart
with that folder's `bench.py --plot`, then re-run this to refresh the dashboard.

Run: .venv/bin/python chapter_7/hypothesis/visualize.py
"""
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.image as mpimg  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent

PANELS = [
    ("h01_category_groupby", "h01_category_groupby.png"),
    ("h02_dask_work_scaling", "h02_dask_work_scaling.png"),
    ("h03_polars_parquet_pushdown", "h03_polars_parquet_pushdown.png"),
    ("h04_category_cardinality", "h04_category_cardinality.png"),
    ("h05_cow_lazy_copy", "h05_cow_lazy_copy.png"),
]


def main():
    fig, axes = plt.subplots(3, 2, figsize=(17, 15))
    for ax, (folder, png) in zip(axes.flat, PANELS):
        ax.axis("off")
        path = HERE / folder / png
        if path.exists():
            ax.imshow(mpimg.imread(path))
        else:
            ax.text(0.5, 0.5, f"missing:\n{folder}\nrun bench.py --plot", ha="center", va="center")
    # blank the unused 6th cell
    for ax in axes.flat[len(PANELS):]:
        ax.axis("off")
    fig.suptitle("Chapter 7 — Hypothesis Lab (Apple Silicon, CPython 3.14, pandas 3.0, polars 1.41)",
                 fontsize=16, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    out = HERE / "hypothesis_dashboard.png"
    fig.savefig(out, dpi=100)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
