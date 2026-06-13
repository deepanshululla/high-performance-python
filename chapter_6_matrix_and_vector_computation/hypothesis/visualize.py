"""Build every hypothesis chart and tile them into one dashboard.

For each hX folder this runs `bench.py --plot` (which measures + saves the folder's
own PNG), then assembles all of them into `hypothesis_dashboard.png` here.

Run: .venv/bin/python chapter_6/hypothesis/visualize.py
"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent

# (folder, saved-png name, short caption for the dashboard)
PANELS = [
    ("h1_reduction_axis_locality", "h1_reduction_axis.png",
     "H1  contiguous vs strided reduction  —  FALSIFIED until 8192²"),
    ("h2_lazy_allocation", "h2_lazy_allocation.png",
     "H2  alloc vs first-touch  —  CONFIRMED (~3000×)"),
    ("h3_numexpr_expression_length", "h3_numexpr_expression_length.png",
     "H3  numexpr vs expression length  —  CONFIRMED (1.4→3.5×)"),
    ("h4_gpu_batching", "h4_gpu_batching.png",
     "H4  GPU batching  —  CONFIRMED (17× cheaper/item)"),
    ("h5_strided_vs_copy", "h5_strided_vs_copy.png",
     "H5  strided view vs copy  —  CONFIRMED (crossover)"),
    ("h6_threading_elementwise_vs_matmul", "h6_threading.png",
     "H6  threads: elementwise vs matmul  —  CONFIRMED"),
]


def refresh_all():
    for folder, _, _ in PANELS:
        bench = HERE / folder / "bench.py"
        print(f"running {folder}/bench.py --plot ...")
        r = subprocess.run([sys.executable, str(bench), "--plot"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  WARN: {folder} failed:\n{r.stderr.strip()[:300]}")


def build_dashboard():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg

    fig, axes = plt.subplots(3, 2, figsize=(20, 16))
    for ax, (folder, png, caption) in zip(axes.flat, PANELS):
        path = HERE / folder / png
        ax.axis("off")
        if path.exists():
            ax.imshow(mpimg.imread(path))
            ax.set_title(caption, fontsize=12, fontweight="bold", pad=6)
        else:
            ax.text(0.5, 0.5, f"{caption}\n\n(no chart — needs a GPU?)",
                    ha="center", va="center", fontsize=12)
    fig.suptitle("Chapter 6 — Hypothesis Lab  (Apple M1 Max, CPython 3.14, numpy 2.4, torch 2.12/MPS)",
                 fontsize=16, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    out = HERE / "hypothesis_dashboard.png"
    fig.savefig(out, dpi=110)
    print(f"\nsaved {out}")


def main():
    if "--no-refresh" not in sys.argv:
        refresh_all()
    build_dashboard()


if __name__ == "__main__":
    main()
