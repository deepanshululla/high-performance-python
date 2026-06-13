"""Tile every Chapter 9 hypothesis chart into a single dashboard.

Each hypothesis folder has its own `benchmark.py --plot` that redraws its chart PNG from the
captured `results.json` (the benchmarks themselves call a live `claude -p` per page, so we never
re-run them here). Regenerate an individual chart with that folder's `benchmark.py --plot`, then
run this to refresh the dashboard.

Run: .venv/bin/python chapter_9_asynchronous_io/hypothesis/visualize.py
"""
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.image as mpimg  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent

PANELS = [
    ("h01_ocr_concurrency", "h01_ocr_concurrency.png"),
    ("h02_gil_process_pool", "h02_gil_process_pool.png"),
    ("h03_multiprocessing_vs_hybrid", "h03_multiprocessing_vs_hybrid.png"),
]


def main():
    fig, axes = plt.subplots(1, 3, figsize=(19, 5))
    for ax, (folder, png) in zip(axes.flat, PANELS):
        ax.axis("off")
        path = HERE / folder / png
        if path.exists():
            ax.imshow(mpimg.imread(path))
        else:
            ax.text(0.5, 0.5, f"missing:\n{folder}\nrun benchmark.py --plot",
                    ha="center", va="center")
    fig.suptitle("Chapter 9 — Hypothesis Lab (real claude -p OCR, single-run; CPython 3.14, Apple Silicon)",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    out = HERE / "hypothesis_dashboard.png"
    fig.savefig(out, dpi=100)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
