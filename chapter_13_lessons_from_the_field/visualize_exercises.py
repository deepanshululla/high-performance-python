"""Generate a chart for every Chapter 13 exercise and tile them into a dashboard.

Each exercise lives in its own folder (chapter_13_lessons_from_the_field/exNN_name/exNN_name.py).
This driver imports each module by path and REUSES its measurement functions, so the charts show
the same numbers the scripts print. It writes `chart.png` into each folder, then assembles
`exercises_dashboard.png` here.

A few exercises are slow to measure (ex01 spins up a local server, ex06/ex09 spawn a fresh process
per RSS reading, ex07 runs a grid search), so regenerating the whole dashboard takes a minute or so;
pass --only to redraw a single exercise while iterating.

Run: .venv/bin/python chapter_13_lessons_from_the_field/visualize_exercises.py
     .venv/bin/python chapter_13_lessons_from_the_field/visualize_exercises.py --only ex07
"""
import argparse
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0]))   # repo root -> vizutil, perf
sys.path.insert(0, str(HERE))               # chapter dir -> _scrape, _rss

from vizutil import plt, setup, save, COLORS  # noqa: E402

GOOD, OK, SLOW, WARN, VIO, RED = (
    COLORS["teal"], COLORS["blue"], COLORS["gray"], COLORS["amber"],
    COLORS["violet"], COLORS["red"],
)


def load(folder):
    d = HERE / folder
    sys.path.insert(0, str(d))
    spec = importlib.util.spec_from_file_location(folder, d / f"{folder}.py")
    mod = importlib.util.module_from_spec(spec)
    # Register before exec so spawn-ed children (peak_rss_mib) can re-import the module
    # and resolve its top-level functions by qualified name.
    sys.modules[folder] = mod
    spec.loader.exec_module(mod)
    return mod


def _barlabels(ax, bars, fmt="{:.0f}", dy=1.02):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() * dy,
                fmt.format(b.get_height()), ha="center", va="bottom", fontsize=8)


def _outpath(folder):
    return str(HERE / folder / "x.py")   # save() writes chart.png next to this


# ---------------------------------------------------------------- ex01 session vs browser

def chart_ex01(_):
    m = load("ex01_session_vs_browser").measure()
    names = ["browser", "session", "async"]
    rates = [m[n]["rate"] for n in names]
    fig, ax = plt.subplots(figsize=(5.0, 4.0))
    bars = ax.bar(names, rates, color=[RED, WARN, GOOD])
    ax.set_yscale("log")
    _barlabels(ax, bars, fmt="{:.0f}", dy=1.05)
    ax.set_ylabel("addresses / second (log)")
    sp = m["async"]["rate"] / m["browser"]["rate"]
    ax.set_title(f"ex01 scraping: session reuse + async\nis {sp:.0f}x the browser path")
    save(fig, _outpath("ex01_session_vs_browser"))


# ---------------------------------------------------------------- ex02 aho-corasick

def chart_ex02(_):
    m = load("ex02_aho_corasick_prefilter").measure()
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(8.4, 3.8))
    rates = [m["brute_rate"], m["aho_rate"]]
    bars = axL.bar(["brute", "Aho-Corasick"], rates, color=[RED, GOOD])
    axL.set_yscale("log")
    _barlabels(axL, bars, fmt="{:.0f}", dy=1.05)
    axL.set_ylabel("tweets / second (log)")
    axL.set_title(f"(A) {m['speedup']:,.0f}x faster")
    evals = [m["n_tweets"] * m["n_keywords"], m["n_tweets"]]
    bars = axR.bar(["brute\n(N×K)", "Aho-Corasick\n(~N scans)"], evals, color=[RED, GOOD])
    axR.set_yscale("log")
    _barlabels(axR, bars, fmt="{:,.0f}", dy=1.05)
    axR.set_ylabel("regex evaluations (log)")
    axR.set_title("(B) the prefilter removes the K factor")
    save(fig, _outpath("ex02_aho_corasick_prefilter"))


# ---------------------------------------------------------------- ex03 spatial index

def chart_ex03(_):
    m = load("ex03_spatial_index_prefilter").measure()
    names = ["exact-all", "bbox\nprefilter", "spatial\nindex"]
    times = [m["exact_s"] * 1e3, m["bbox_s"] * 1e3, m["index_s"] * 1e3]
    fig, ax = plt.subplots(figsize=(5.2, 4.0))
    bars = ax.bar(names, times, color=[RED, WARN, GOOD])
    ax.set_yscale("log")
    for b, sp in zip(bars, [1.0, m["bbox_speedup"], m["index_speedup"]]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.05,
                f"{b.get_height():.2f} ms\n{sp:.0f}x", ha="center", va="bottom", fontsize=8)
    ax.set_ylabel("query time (ms, log)")
    ax.set_title("ex03 approximate-then-exact:\neach rung an order of magnitude")
    save(fig, _outpath("ex03_spatial_index_prefilter"))


# ---------------------------------------------------------------- ex04 branchless masks

def chart_ex04(_):
    m = load("ex04_branchless_masks").measure()
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(8.4, 3.8))
    names = ["python\nloop", "numpy\nboolean", "numpy\nbranchless"]
    times = [m["python_loop"] * 1e3, m["numpy_boolean"] * 1e3, m["numpy_branchless"] * 1e3]
    bars = axL.bar(names, times, color=[SLOW, GOOD, WARN])
    axL.set_yscale("log")
    _barlabels(axL, bars, fmt="{:.2f}", dy=1.05)
    axL.set_ylabel("time (ms, log)")
    axL.set_title(f"(A) vectorising is {m['vectorize_speedup']:.0f}x")
    bars = axR.bar(["boolean", "branchless"], [m["numpy_boolean"] * 1e3, m["numpy_branchless"] * 1e3],
                   color=[GOOD, WARN])
    _barlabels(axR, bars, fmt="{:.2f} ms", dy=1.01)
    axR.set_ylabel("time (ms)")
    axR.set_title(f"(B) branchless is {m['branchless_vs_boolean']:.2f}x — a CPU loss")
    save(fig, _outpath("ex04_branchless_masks"))


# ---------------------------------------------------------------- ex05 loop fusion

def chart_ex05(_):
    m = load("ex05_numba_loop_fusion").measure()
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(8.4, 3.8))
    names = ["python\nloop", "numpy", "numba\nauto", "numba\nmanual"]
    times = [m["python_loop"] * 1e3, m["numpy"] * 1e3, m["numba_auto"] * 1e3, m["numba_manual"] * 1e3]
    bars = axL.bar(names, times, color=[SLOW, RED, GOOD, OK])
    axL.set_yscale("log")
    _barlabels(axL, bars, fmt="{:.2f}", dy=1.05)
    axL.set_ylabel("time (ms, log)")
    axL.set_title("(A) auto == manual: fusion IS the loop")
    bars = axR.bar(["numpy", "numba"], [m["numpy"] * 1e3, m["numba_auto"] * 1e3], color=[RED, GOOD])
    _barlabels(axR, bars, fmt="{:.2f} ms", dy=1.01)
    axR.set_ylabel("time (ms)")
    axR.set_title(f"(B) loop fusion: {m['fusion_speedup']:.1f}x, no temporaries")
    save(fig, _outpath("ex05_numba_loop_fusion"))


# ---------------------------------------------------------------- ex06 as-of matmul

def chart_ex06(_):
    m = load("ex06_asof_matmul").measure()
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(8.6, 3.8))
    names = ["numpy\nbroadcast", "python\nloop", "numba\nasof"]
    rss = [m["numpy"]["rss_mib"], m["python"]["rss_mib"], m["numba"]["rss_mib"]]
    bars = axL.bar(names, rss, color=[RED, OK, GOOD])
    _barlabels(axL, bars, fmt="{:.0f}", dy=1.01)
    floor = m["python"]["rss_mib"]
    axL.axhline(floor, color=SLOW, ls="--", lw=1, label="real inputs (~floor)")
    axL.set_ylabel("peak RSS (MiB)")
    axL.legend()
    axL.set_title(f"(A) broadcast blows up by\nthe {m['broadcast_mib']:.0f} MiB (T,N,N) temp")
    times = [m["numpy"]["s"] * 1e3, m["python"]["s"] * 1e3, m["numba"]["s"] * 1e3]
    bars = axR.bar(names, times, color=[RED, OK, GOOD])
    _barlabels(axR, bars, fmt="{:.0f}", dy=1.01)
    axR.set_ylabel("time (ms)")
    axR.set_title("(B) numba wins speed too")
    save(fig, _outpath("ex06_asof_matmul"))


# ---------------------------------------------------------------- ex07 wrong problem

def chart_ex07(_):
    m = load("ex07_wrong_problem_proxy").measure()
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(8.4, 3.8))
    bars = axL.bar(["ML grid\nsearch", "carts\nproxy"],
                   [m["model"]["bad_days"], m["proxy"]["bad_days"]], color=[RED, GOOD])
    _barlabels(axL, bars, fmt="{:.0f}", dy=1.02)
    axL.set_ylabel(f"days off by > {m['tolerance']} trucks")
    axL.set_title(f"(A) the proxy is more accurate\n({m['test_days']} test days)")
    times = [max(m["model"]["seconds"], 1e-6), max(m["proxy"]["seconds"], 1e-6)]
    bars = axR.bar(["ML grid\nsearch", "carts\nproxy"], times, color=[RED, GOOD])
    axR.set_yscale("log")
    _barlabels(axR, bars, fmt="{:.4f}s", dy=1.1)
    axR.set_ylabel("compute (s, log)")
    axR.set_title(f"(B) ~{m['speedup']:,.0f}x less compute")
    save(fig, _outpath("ex07_wrong_problem_proxy"))


# ---------------------------------------------------------------- ex08 defensive pandera

def chart_ex08(_):
    m = load("ex08_defensive_pandera").measure()
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(8.4, 3.8))
    bars = axL.bar(["truth", "unguarded\n(dirty)"], [m["truth"], m["silent_wrong"]],
                   color=[GOOD, RED])
    _barlabels(axL, bars, fmt="{:.2f}", dy=1.005)
    axL.set_ylim(min(m["truth"], m["silent_wrong"]) * 0.97, max(m["truth"], m["silent_wrong"]) * 1.02)
    axL.set_ylabel("portfolio risk score")
    axL.set_title(f"(A) silent {m['rel_error_pct']:.1f}% error,\n{m['caught']:,} violations caught")
    bars = axR.bar(["validate", "compute"], [m["validate_s"] * 1e3, m["compute_s"] * 1e3],
                   color=[OK, SLOW])
    axR.set_yscale("log")
    _barlabels(axR, bars, fmt="{:.2f} ms", dy=1.1)
    axR.set_ylabel("time (ms, log)")
    axR.set_title(f"(B) validation: {m['validate_rows_per_s']/1e6:.0f}M rows/s")
    save(fig, _outpath("ex08_defensive_pandera"))


# ---------------------------------------------------------------- ex09 streaming

def chart_ex09(_):
    m = load("ex09_streaming_generators").measure()
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(8.4, 3.8))
    rss = [m["materialised"]["rss_mib"], max(m["streamed"]["rss_mib"], 0.05)]
    bars = axL.bar(["materialised\n(list)", "streamed\n(generator)"], rss, color=[RED, GOOD])
    axL.set_yscale("log")
    _barlabels(axL, bars, fmt="{:.1f}", dy=1.1)
    axL.axhline(m["corpus_mib"], color=SLOW, ls="--", lw=1, label="raw float data")
    axL.set_ylabel("peak RSS (MiB, log)")
    axL.legend()
    axL.set_title(f"(A) generator holds one vector\n({m['mem_ratio']:.0f}x less RAM)")
    times = [m["materialised"]["s"] * 1e3, m["streamed"]["s"] * 1e3]
    bars = axR.bar(["materialised", "streamed"], times, color=[RED, GOOD])
    _barlabels(axR, bars, fmt="{:.0f} ms", dy=1.01)
    axR.set_ylabel("time (ms)")
    axR.set_title("(B) same speed — the saving is free")
    save(fig, _outpath("ex09_streaming_generators"))


# ---------------------------------------------------------------- ex10 BLAS

def chart_ex10(_):
    m = load("ex10_know_your_blas").measure()
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(8.6, 3.8))
    names = ["python\nloop", "numba\nloop", "numpy\nBLAS"]
    gf = [m["python"]["gflops"], m["numba"]["gflops"], m["numpy"]["gflops"]]
    bars = axL.bar(names, gf, color=[SLOW, WARN, GOOD])
    axL.set_yscale("log")
    _barlabels(axL, bars, fmt="{:.2f}", dy=1.1)
    axL.set_ylabel("GFLOP/s (log)")
    axL.set_title(f"(A) compiled loop still {m['numba_vs_blas']:.0f}x\nshort of BLAS")
    bars = axR.bar(["compiled\nloop", "BLAS\n(2000²)"], [m["numba"]["gflops"], m["blas_big_gflops"]],
                   color=[WARN, GOOD])
    _barlabels(axR, bars, fmt="{:.0f}", dy=1.02)
    axR.set_ylabel("GFLOP/s")
    axR.set_title("(B) BLAS reaches real hardware throughput")
    save(fig, _outpath("ex10_know_your_blas"))


CHARTS = {
    "ex01": chart_ex01, "ex02": chart_ex02, "ex03": chart_ex03, "ex04": chart_ex04,
    "ex05": chart_ex05, "ex06": chart_ex06, "ex07": chart_ex07, "ex08": chart_ex08,
    "ex09": chart_ex09, "ex10": chart_ex10,
}

FOLDERS = {
    "ex01": "ex01_session_vs_browser", "ex02": "ex02_aho_corasick_prefilter",
    "ex03": "ex03_spatial_index_prefilter", "ex04": "ex04_branchless_masks",
    "ex05": "ex05_numba_loop_fusion", "ex06": "ex06_asof_matmul",
    "ex07": "ex07_wrong_problem_proxy", "ex08": "ex08_defensive_pandera",
    "ex09": "ex09_streaming_generators", "ex10": "ex10_know_your_blas",
}


def build_dashboard():
    import matplotlib.image as mpimg
    fig, axes = plt.subplots(4, 3, figsize=(18, 16))
    for ax, key in zip(axes.flat, list(FOLDERS) + [None] * 2):
        ax.axis("off")
        if key is None:
            continue
        png = HERE / FOLDERS[key] / "chart.png"
        if png.exists():
            ax.imshow(mpimg.imread(png))
    fig.suptitle("Chapter 13 — Lessons from the Field: exercise dashboard",
                 fontsize=16, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    out = HERE / "exercises_dashboard.png"
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {out}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="run a single exercise, e.g. ex07")
    parser.add_argument("--no-dashboard", action="store_true")
    args = parser.parse_args()
    setup()
    todo = {args.only: CHARTS[args.only]} if args.only else CHARTS
    for key, fn in todo.items():
        print(f"== {key} ==")
        fn(None)
    if not args.only and not args.no_dashboard:
        build_dashboard()


if __name__ == "__main__":
    main()
