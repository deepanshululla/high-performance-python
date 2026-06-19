"""Generate a chart for every Chapter 12 exercise and tile them into a dashboard.

Each exercise lives in its own folder (chapter_12_using_less_ram/exNN_name/exNN_name.py).
This driver imports each module by path and REUSES its measurement functions, so the charts
show the same numbers the scripts print. It writes `chart.png` into each folder, then
assembles `exercises_dashboard.png` here.

Several exercises measure peak RSS by spawning a fresh child process per allocation (see
`_mem.py`), so regenerating the whole dashboard re-runs those allocations and takes a couple
of minutes; pass --only to redraw a single exercise while iterating.

Run: .venv/bin/python chapter_12_using_less_ram/visualize_exercises.py
     .venv/bin/python chapter_12_using_less_ram/visualize_exercises.py --only ex07
"""
import argparse
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0]))   # repo root -> vizutil, perf
sys.path.insert(0, str(HERE))               # chapter dir -> _mem, _tokens, _pds

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
    # and resolve its top-level builder functions by qualified name.
    sys.modules[folder] = mod
    spec.loader.exec_module(mod)
    return mod


def _barlabels(ax, bars, fmt="{:.0f}", dy=1.01):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() * dy,
                fmt.format(b.get_height()), ha="center", va="bottom", fontsize=8)


def _outpath(folder):
    return str(HERE / folder / "x.py")   # save() writes chart.png next to this


# ---------------------------------------------------------------- ex01 primitives

def chart_ex01(_):
    m = load("ex01_primitives_cost")
    d = m.measure()
    labels = list(d.keys())
    vals = [max(d[k], 0.05) for k in labels]   # floor so log scale renders the ~0 zeros bar
    colors = [SLOW, GOOD, GOOD, WARN]
    fig, ax = plt.subplots(figsize=(4.6, 3.8))
    bars = ax.bar(range(len(labels)), vals, color=colors)
    ax.set_yscale("log")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels([l.replace(" ", "\n") for l in labels], fontsize=8)
    _barlabels(ax, bars, fmt="{:.0f}", dy=1.05)
    ax.set_ylabel("peak RSS (MiB, log)")
    ax.set_title(f"ex01 100M ints: list is {d['list']/d['numpy int64']:.0f}x numpy")
    save(fig, _outpath("ex01_primitives_cost"))


# ---------------------------------------------------------------- ex02 numexpr

def chart_ex02(_):
    m = load("ex02_numexpr_temporaries")
    d = m.measure()
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(8.2, 3.8))
    names = ["numpy", "numexpr"]
    peaks = [d[n]["peak_mib"] for n in names]
    bars = axL.bar(names, peaks, color=[RED, GOOD])
    _barlabels(axL, bars, fmt="{:.0f}")
    floor = min(peaks)
    axL.axhline(floor, color=SLOW, ls="--", lw=1, label="inputs+result floor")
    axL.set_ylabel("peak RSS (MiB)")
    axL.legend()
    axL.set_title("(A) peak RAM: numexpr has no temporaries")
    times = [d[n]["time_s"] for n in names]
    bars = axR.bar(names, times, color=[RED, GOOD])
    axR.set_yscale("log")
    _barlabels(axR, bars, fmt="{:.3f}s", dy=1.05)
    axR.set_ylabel("eval time (s, log)")
    axR.set_title(f"(B) speed: {d['numpy']['time_s']/d['numexpr']['time_s']:.1f}x faster")
    save(fig, _outpath("ex02_numexpr_temporaries"))


# ---------------------------------------------------------------- ex03 getsizeof

def chart_ex03(_):
    m = load("ex03_getsizeof_vs_asizeof")
    d = m.measure()
    labels = list(d.keys())
    vals = [d[k] for k in labels]
    fig, ax = plt.subplots(figsize=(4.8, 3.8))
    bars = ax.bar([l.split(" ")[0] for l in labels], vals, color=[RED, OK, GOOD])
    _barlabels(ax, bars, fmt="{:.0f} MiB", dy=1.01)
    ax.set_ylabel("reported size (MiB)")
    ax.set_title("ex03 sizing 10M ints: getsizeof\nsees only the pointers")
    save(fig, _outpath("ex03_getsizeof_vs_asizeof"))


# ---------------------------------------------------------------- ex04 unicode

def chart_ex04(_):
    m = load("ex04_bytes_vs_unicode")
    d = m.measure()
    labels = list(d.keys())
    vals = [d[k][0] for k in labels]
    bpc = [d[k][1] for k in labels]
    colors = [GOOD, GOOD, OK, RED, SLOW]
    fig, ax = plt.subplots(figsize=(5.2, 3.8))
    bars = ax.bar(range(len(labels)), vals, color=colors)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels([l.replace(" ", "\n") for l in labels], fontsize=8)
    _barlabels(ax, bars, fmt="{:.0f}")
    for b, c in zip(bars, bpc):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() * 0.5,
                f"{c:.0f}B/ch", ha="center", va="center", fontsize=8, color="white")
    ax.set_ylabel("peak RSS (MiB)")
    ax.set_title("ex04 100M chars: width set by\nthe widest character (PEP 393)")
    save(fig, _outpath("ex04_bytes_vs_unicode"))


# ---------------------------------------------------------------- ex05 containers

def chart_ex05(_):
    m = load("ex05_text_containers")
    d = m.measure()
    fig, ax = plt.subplots(figsize=(5.4, 4.0))
    palette = {"list (linear)": RED, "list+bisect": WARN, "set": OK,
               "dict": VIO, "trie (build)": SLOW, "trie (load)": GOOD}
    for name, row in d.items():
        ax.scatter(row["rss_mib"], row["lookup_us"], s=90,
                   color=palette.get(name, OK), zorder=3)
        ax.annotate(name, (row["rss_mib"], row["lookup_us"]),
                    textcoords="offset points", xytext=(6, 4), fontsize=8)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("RAM (MiB, log)")
    ax.set_ylabel("lookup time (µs, log)")
    ax.set_title("ex05 text containers: loaded trie\nwins both axes (lower-left)")
    save(fig, _outpath("ex05_text_containers"))


# ---------------------------------------------------------------- ex06 featurehasher

def chart_ex06(_):
    m = load("ex06_featurehasher")
    d = m.measure()
    names = ["DictVectorizer", "FeatureHasher"]
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(8.4, 3.8))
    import numpy as np
    x = np.arange(len(names))
    builds = [d[n]["build_s"] for n in names]
    trains = [d[n]["train_s"] for n in names]
    axL.bar(x - 0.2, builds, 0.4, color=OK, label="build")
    axL.bar(x + 0.2, trains, 0.4, color=VIO, label="train")
    axL.set_xticks(x)
    axL.set_xticklabels(["DictVect", "FeatHash"])
    axL.set_ylabel("seconds")
    axL.legend()
    axL.set_title("(A) FeatureHasher builds/trains faster")
    accs = [d[n]["score"] for n in names]
    bars = axR.bar(["DictVect", "FeatHash"], accs, color=[OK, GOOD])
    _barlabels(axR, bars, fmt="{:.3f}", dy=1.005)
    axR.set_ylim(0, 1.05)
    axR.set_ylabel("test accuracy")
    axR.set_title("(B) identical accuracy, no vocabulary")
    save(fig, _outpath("ex06_featurehasher"))


# ---------------------------------------------------------------- ex07 sparse

def chart_ex07(_):
    m = load("ex07_sparse_matrix")
    rows = m.measure()
    dens = [r["density"] for r in rows]
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(8.6, 3.8))
    axL.plot(dens, [r["t_sparse"] * 1e3 for r in rows], "o-", color=GOOD, label="sparse")
    axL.plot(dens, [r["t_dense"] * 1e3 for r in rows], "s-", color=RED, label="dense")
    axL.set_xscale("log")
    axL.set_yscale("log")
    axL.set_xlabel("density")
    axL.set_ylabel("multiply time (ms, log)")
    axL.legend()
    axL.set_title("(A) sparse wins only when very sparse")
    axR.plot(dens, [r["mem_sparse_mib"] for r in rows], "o-", color=GOOD, label="sparse")
    axR.axhline(rows[0]["mem_dense_mib"], color=RED, ls="--", lw=1.2, label="dense (fixed)")
    axR.set_xscale("log")
    axR.set_xlabel("density")
    axR.set_ylabel("memory (MiB)")
    axR.legend()
    axR.set_title("(B) sparse saves memory much longer")
    save(fig, _outpath("ex07_sparse_matrix"))


# ---------------------------------------------------------------- ex08 morris

def chart_ex08(_):
    m = load("ex08_morris_counter")
    d = m.measure()
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(8.6, 3.8))
    iters, samples = d["iters"], d["samples"]
    for i, ys in samples.items():
        axL.plot(iters, ys, ".:", color=SLOW, lw=0.9, alpha=0.8)
    axL.plot(iters, iters, "-", color=RED, lw=1.6, label="true count")
    axL.set_xscale("log")
    axL.set_yscale("log")
    axL.set_xlabel("true count (log)")
    axL.set_ylabel("estimate (log)")
    axL.legend()
    axL.set_title("(A) 1-byte counters track the count, noisily")
    err = d["error"]
    counts = [f"{r['true']:,}" for r in err]
    rels = [r["rel_err"] * 100 for r in err]
    bars = axR.bar(counts, rels, color=WARN)
    _barlabels(axR, bars, fmt="{:.0f}%")
    axR.axhline(100 / (2 ** 0.5), color=SLOW, ls="--", lw=1, label="1/√2 ≈ 71%")
    axR.set_ylabel("relative error (σ/true, %)")
    axR.legend()
    axR.set_title("(B) error ~constant across magnitudes")
    save(fig, _outpath("ex08_morris_counter"))


# ---------------------------------------------------------------- ex09 bloom

def chart_ex09(_):
    m = load("ex09_bloom_filter")
    d = m.measure()
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(8.6, 3.8))
    rows = d["fp_vs_fill"]
    fills = [r["fill"] for r in rows]
    fps = [r["fp_rate"] * 100 for r in rows]
    axL.plot(fills, fps, "o-", color=RED)
    axL.axhline(0.5, color=GOOD, ls="--", lw=1, label="target 0.5%")
    axL.axvline(1.0, color=SLOW, ls=":", lw=1, label="capacity")
    axL.set_xlabel("fill (fraction of capacity)")
    axL.set_ylabel("false-positive rate (%)")
    axL.legend()
    axL.set_title("(A) FP balloons past capacity")
    sc = d["scaling"]
    bars = axR.bar(["plain", "scaling"], [sc["plain_fp"] * 100, sc["scaling_fp"] * 100],
                   color=[RED, GOOD])
    _barlabels(axR, bars, fmt="{:.1f}%")
    axR.axhline(sc["target"] * 100, color=SLOW, ls="--", lw=1, label="target")
    axR.set_ylabel("false-positive rate (%)")
    axR.legend()
    axR.set_title(f"(B) {sc['n_added']:,} items, {sc['capacity']:,} cap")
    save(fig, _outpath("ex09_bloom_filter"))


# ---------------------------------------------------------------- ex10 hyperloglog

def chart_ex10(_):
    m = load("ex10_hyperloglog")
    d = m.measure()
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(8.8, 3.8))
    h2h = d["head_to_head"]
    names = [r["name"].replace(" ", "\n") for r in h2h]
    ests = [r["est"] for r in h2h]
    true = next(r["est"] for r in h2h if "set" in r["name"])
    bars = axL.bar(range(len(names)), ests,
                   color=[RED, OK, GOOD, VIO, SLOW][:len(names)])
    axL.axhline(true, color=SLOW, ls="--", lw=1, label=f"true {true:,}")
    axL.set_yscale("log")
    axL.set_xticks(range(len(names)))
    axL.set_xticklabels(names, fontsize=7)
    axL.set_ylabel("estimate (log)")
    axL.legend()
    axL.set_title("(A) one register is hopeless; the rest land close")
    sweep = d["hll_sweep"]
    regs = [r["registers"] for r in sweep]
    axR.plot(regs, [r["mean_abs_err"] * 100 for r in sweep], "o-", color=GOOD,
             label="measured")
    axR.plot(regs, [r["theory"] * 100 for r in sweep], "s--", color=SLOW,
             label="1.04/√m")
    axR.set_xscale("log")
    axR.set_yscale("log")
    axR.set_xlabel("registers (= bytes, log)")
    axR.set_ylabel("error (%, log)")
    axR.legend()
    axR.set_title("(B) HyperLogLog error tracks 1.04/√m")
    save(fig, _outpath("ex10_hyperloglog"))


CHARTS = {
    "ex01": chart_ex01, "ex02": chart_ex02, "ex03": chart_ex03, "ex04": chart_ex04,
    "ex05": chart_ex05, "ex06": chart_ex06, "ex07": chart_ex07, "ex08": chart_ex08,
    "ex09": chart_ex09, "ex10": chart_ex10,
}

FOLDERS = {
    "ex01": "ex01_primitives_cost", "ex02": "ex02_numexpr_temporaries",
    "ex03": "ex03_getsizeof_vs_asizeof", "ex04": "ex04_bytes_vs_unicode",
    "ex05": "ex05_text_containers", "ex06": "ex06_featurehasher",
    "ex07": "ex07_sparse_matrix", "ex08": "ex08_morris_counter",
    "ex09": "ex09_bloom_filter", "ex10": "ex10_hyperloglog",
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
    fig.suptitle("Chapter 12 — Using Less RAM: exercise dashboard",
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
