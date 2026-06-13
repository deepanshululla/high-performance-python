"""Generate a chart for every Chapter 7 exercise and tile them into a dashboard.

Each exercise lives in its own folder (chapter_7/exNN_name/exNN_name.py). This driver
imports each module by path, REUSES its functions to measure the key comparison, saves
`chart.png` into that folder, then assembles `exercises_dashboard.png` here.

Because ex08 uses Dask's `processes` scheduler (which spawns workers), this whole script
MUST stay under `if __name__ == "__main__"`.

Run: .venv/bin/python chapter_7/visualize_exercises.py
     .venv/bin/python chapter_7/visualize_exercises.py --only ex03   # one exercise
"""
import importlib.util
import pathlib
import sys
import timeit
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")

HERE = pathlib.Path(__file__).resolve().parent
C = {"slow": "#7f7f7f", "pd": "#1f77b4", "alt": "#17becf", "good": "#2ca02c",
     "bad": "#d62728", "warn": "#ff7f0e", "violet": "#9467bd"}


def load(folder):
    path = HERE / folder / f"{folder}.py"
    spec = importlib.util.spec_from_file_location(folder, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def best(fn, reps=2, warmup=0):
    for _ in range(warmup):
        fn()
    import time
    b = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        b = min(b, time.perf_counter() - t)
    return b


def barlabels(ax, bars, fmt="{:.1f}", dy=1.02):
    for b in bars:
        h = b.get_height()
        ax.text(b.get_x() + b.get_width() / 2, h * dy, fmt.format(h),
                ha="center", va="bottom", fontsize=8)


# ---------------------------------------------------------------- per exercise
def ex01(ax):
    m = load("ex01_ols_sklearn_vs_lstsq")
    row = m.gen_data(1)[0]
    n = 1500
    t_sk = timeit.timeit(lambda: m.ols_sklearn(row), number=n) / n * 1e6
    t_ls = timeit.timeit(lambda: m.ols_lstsq(row), number=n) / n * 1e6
    bars = ax.bar(["sklearn\nLinearRegression", "numpy\nlinalg.lstsq"], [t_sk, t_ls],
                  color=[C["slow"], C["good"]])
    ax.set_yscale("log"); ax.set_ylabel("per call (µs, log)")
    ax.set_title(f"ex01 — sklearn vs lstsq ({t_sk / t_ls:.0f}× on the same solve)")
    barlabels(ax, bars, "{:.1f}")


def ex02(ax):
    m = load("ex02_row_iteration")
    df = m.gen_df()
    cases = [("iloc", m.via_iloc, C["bad"]), ("iterrows", m.via_iterrows, C["bad"]),
             ("apply", m.via_apply, C["pd"]), ("apply\nraw=True", m.via_apply_raw, C["good"])]
    times = [best(lambda fn=fn: fn(df)) for _, fn, _ in cases]
    bars = ax.bar([c[0] for c in cases], times, color=[c[2] for c in cases])
    ax.set_ylabel("time (s)")
    ax.set_title(f"ex02 — row iteration ({df.shape[0]:,} rows)")
    barlabels(ax, bars, "{:.2f}")


def ex03(ax):
    m = load("ex03_numba_compile")
    df = m.gen_df()
    cases = [("apply raw\n(no compile)", m.run_plain, C["pd"]),
             ("jit\nprecompiled", m.run_jit, C["alt"]),
             ("engine=\n'numba'", m.run_engine, C["warn"]),
             ("engine=numba\nparallel", m.run_engine_parallel, C["good"])]
    times = [best(lambda fn=fn: fn(df), reps=3, warmup=1) * 1e3 for _, fn, _ in cases]
    bars = ax.bar([c[0] for c in cases], times, color=[c[2] for c in cases])
    ax.set_yscale("log"); ax.set_ylabel("time (ms, log)")
    ax.set_title(f"ex03 — Numba compile arc ({times[0] / times[-1]:.0f}× total)")
    barlabels(ax, bars, "{:.0f}")


def ex04(ax):
    m = load("ex04_concat_quadratic")
    chunks = m.concat_chunk_times()
    x = [(k + 1) * 10 for k in range(len(chunks))]
    y = [c * 1e3 for c in chunks]
    ax.plot(x, y, "o-", color=C["bad"], linewidth=2)
    ax.fill_between(x, y, color=C["bad"], alpha=0.12)
    ax.set_xlabel("% of concatenations done"); ax.set_ylabel("time for this 10% (ms)")
    ax.set_title(f"ex04 — concat cost grows with length ({y[-1] / y[0]:.1f}× by the end)")
    ax.set_ylim(bottom=0)


def ex05(ax):
    m = load("ex05_str_apply_vs_chain")
    s = m.gen_str_series()
    n = 15
    t_chain = timeit.timeit(lambda: m.via_str_chain(s), number=n) / n * 1e3
    t_apply = timeit.timeit(lambda: m.via_apply(s), number=n) / n * 1e3
    bars = ax.bar([".str chain\n(split+find)", "apply\n(find_9)"], [t_chain, t_apply],
                  color=[C["slow"], C["good"]])
    ax.set_ylabel("time (ms)")
    ax.set_title(f"ex05 — str ops ({t_chain / t_apply:.1f}× on pandas 3.0)")
    barlabels(ax, bars, "{:.1f}")


def ex06(ax):
    m = load("ex06_nan_int_promotion")
    mem = m.memories()
    labels = list(mem.keys())
    vals = [v / 1024 for v in mem.values()]
    bars = ax.bar(labels, vals, color=[C["good"], C["bad"], C["warn"]])
    ax.set_ylabel("memory (KB)")
    ax.set_title("ex06 — one NaN promotes int64 → float64")
    barlabels(ax, bars, "{:.0f}")
    ax.text(0.5, 0.92, "float64 loses integer precision past 2⁵³",
            transform=ax.transAxes, ha="center", fontsize=8.5, color=C["bad"])


def ex07(ax):
    m = load("ex07_arrow_vs_numpy_strings")
    sm = m.string_memory()
    labels = ["object\n(NumPy)", "string\n[pyarrow]", "category"]
    vals = [v / 1e6 for v in sm.values()]
    bars = ax.bar(labels, vals, color=[C["bad"], C["pd"], C["good"]])
    ax.set_yscale("log"); ax.set_ylabel("memory (MB, log)")
    ax.set_title(f"ex07 — string storage ({vals[0] / vals[1]:.0f}× / {vals[0] / vals[2]:.0f}× smaller)")
    barlabels(ax, bars, "{:.2f}")


def ex08(ax):
    m = load("ex08_dask_parallel_apply")
    df = m.gen_big()
    t_pd = best(lambda: m.run_pandas(df))
    t_th = best(lambda: m.run_dask(df, "threads"), warmup=1)
    t_pr = best(lambda: m.run_dask(df, "processes"), warmup=1)
    bars = ax.bar(["pandas\n1 thread", "dask\nthreads", "dask\nprocesses"],
                  [t_pd, t_th, t_pr], color=[C["pd"], C["bad"], C["good"]])
    ax.set_ylabel("time (s)")
    ax.set_title(f"ex08 — Dask apply ({len(df):,} rows)")
    barlabels(ax, bars, "{:.1f}")
    ax.text(0.5, 0.92, "threads can't beat the GIL; processes can",
            transform=ax.transAxes, ha="center", fontsize=8.5, color=C["good"])


def ex09(ax):
    m = load("ex09_polars_vs_pandas")
    pdf, pldf = m.gen_frames()
    t_pd = best(lambda: m.pandas_query(pdf), reps=3, warmup=1) * 1e3
    t_pe = best(lambda: m.polars_eager(pldf), reps=3, warmup=1) * 1e3
    t_pl = best(lambda: m.polars_lazy(pldf), reps=3, warmup=1) * 1e3
    bars = ax.bar(["pandas", "polars\neager", "polars\nlazy"], [t_pd, t_pe, t_pl],
                  color=[C["pd"], C["violet"], C["good"]])
    ax.set_ylabel("time (ms)")
    ax.set_title(f"ex09 — multi-step query ({t_pd / t_pe:.1f}× via Polars)")
    barlabels(ax, bars, "{:.0f}")


EXERCISES = [
    ("ex01_ols_sklearn_vs_lstsq", ex01), ("ex02_row_iteration", ex02),
    ("ex03_numba_compile", ex03), ("ex04_concat_quadratic", ex04),
    ("ex05_str_apply_vs_chain", ex05), ("ex06_nan_int_promotion", ex06),
    ("ex07_arrow_vs_numpy_strings", ex07), ("ex08_dask_parallel_apply", ex08),
    ("ex09_polars_vs_pandas", ex09),
]


def save_one(folder, fn):
    fig, ax = plt.subplots(figsize=(6, 4))
    fn(ax)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    out = HERE / folder / "chart.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"saved {out}")


def main():
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]

    todo = [(f, fn) for f, fn in EXERCISES if only is None or only in f]
    for folder, fn in todo:
        try:
            save_one(folder, fn)
        except Exception as e:
            print(f"  WARN {folder}: {type(e).__name__}: {e}")

    if only:
        return
    # dashboard: tile all 9 saved charts (3 rows x 3 cols)
    import matplotlib.image as mpimg
    fig, axes = plt.subplots(3, 3, figsize=(20, 16))
    for ax, (folder, _) in zip(axes.flat, EXERCISES):
        ax.axis("off")
        png = HERE / folder / "chart.png"
        if png.exists():
            ax.imshow(mpimg.imread(png))
    fig.suptitle("Chapter 7 — Pandas / Dask / Polars (Apple Silicon, CPython 3.14, "
                 "pandas 3.0, polars 1.41, numba 0.65)", fontsize=17, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    out = HERE / "exercises_dashboard.png"
    fig.savefig(out, dpi=100)
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
