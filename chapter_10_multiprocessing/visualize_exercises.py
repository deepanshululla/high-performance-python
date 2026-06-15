"""Generate a chart for every Chapter 10 exercise and tile them into a dashboard.

Each exercise lives in its own folder (chapter_10_multiprocessing/exNN_name/exNN_name.py).
This driver imports each module by path and REUSES its measurement functions, so the charts
show the same numbers the scripts print. It writes `chart.png` into each folder, then
assembles `exercises_dashboard.png` here.

ex07 re-measures the 18-digit prime checks and takes ~70s; pass --only to skip it while
iterating on the others.

Run: .venv/bin/python chapter_10_multiprocessing/visualize_exercises.py
     .venv/bin/python chapter_10_multiprocessing/visualize_exercises.py --only ex05
"""
import argparse
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0]))   # repo root -> vizutil, perf
sys.path.insert(0, str(HERE))               # chapter dir -> _pi, _primes, _mp

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
    # Register before exec so that worker functions defined in this module pickle
    # by reference correctly when a Pool ships a task (ex07, ex08) — otherwise the
    # forked worker can't resolve "<folder>.worker_fn" back to the same object.
    sys.modules[folder] = mod
    spec.loader.exec_module(mod)
    return mod


def _barlabels(ax, bars, fmt="{:.2f}", dy=1.01):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() * dy,
                fmt.format(b.get_height()), ha="center", va="bottom", fontsize=9)


def chart_ex01(_):
    m = load("ex01_pi_threads_vs_processes")
    t = m.measure()
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    bars = ax.bar(["serial", "threads", "processes"],
                  [t["serial"], t["threads"], t["processes"]],
                  color=[SLOW, RED, GOOD])
    _barlabels(ax, bars, fmt="{:.2f}s")
    ax.set_ylabel("seconds")
    sp = t["serial"] / t["processes"]
    ax.set_title(f"ex01 pure-Python pi, {m.WORKERS} workers\n"
                 f"threads {t['serial'] / t['threads']:.2f}x (GIL), procs {sp:.1f}x")
    save(fig, str(HERE / "ex01_pi_threads_vs_processes" / "x.py"))


def chart_ex02(_):
    m = load("ex02_process_scaling")
    rows = m.sweep()
    base = rows[0][1]
    xs = [w for w, _ in rows]
    speed = [base / t for _, t in rows]
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    ax.plot(xs, speed, "o-", color=GOOD, label="measured speedup")
    ax.plot(xs, xs, "--", color=SLOW, lw=1, label="ideal (n x)")
    ax.axvline(8, color=VIO, ls=":", lw=1)
    ax.text(8, 1, " 8 P-cores", color=VIO, fontsize=8, rotation=90, va="bottom")
    ax.set_xlabel("worker processes")
    ax.set_ylabel("speedup vs serial")
    ax.legend()
    ax.set_title(f"ex02 process scaling\npeak {max(speed):.1f}x (8P + 2E cores)")
    save(fig, str(HERE / "ex02_process_scaling" / "x.py"))


def chart_ex03(_):
    m = load("ex03_pi_numpy")
    t = m.measure()
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    bars = ax.bar(["serial", "threads", "processes"],
                  [t["serial"], t["threads"], t["processes"]],
                  color=[SLOW, OK, GOOD])
    _barlabels(ax, bars, fmt="{:.2f}s")
    ax.set_ylabel("seconds")
    ax.set_title(f"ex03 numpy pi, {m.WORKERS} workers\n"
                 f"threads {t['serial'] / t['threads']:.2f}x (GIL released), "
                 f"procs {t['serial'] / t['processes']:.2f}x")
    save(fig, str(HERE / "ex03_pi_numpy" / "x.py"))


def chart_ex04(_):
    m = load("ex04_joblib")
    res = m.measure()
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    bars = ax.bar(["parallel", "cache\ncold", "cache\nwarm"],
                  [res["parallel"], res["cold"], res["warm"]],
                  color=[OK, WARN, GOOD])
    ax.set_yscale("log")
    _barlabels(ax, bars, fmt="{:.2f}s", dy=1.05)
    ax.set_ylabel("seconds (log)")
    ax.set_title(f"ex04 Joblib\nwarm cache {res['cold'] / res['warm']:.0f}x faster")
    save(fig, str(HERE / "ex04_joblib" / "x.py"))


def chart_ex05(_):
    m = load("ex05_chunksize")
    serial = m.measure_serial()
    rows, default = m.sweep_chunksize()
    xs = [cs for cs, _ in rows]
    speed = [serial / t for _, t in rows]
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    ax.plot(xs, speed, "o-", color=GOOD)
    ax.axhline(serial / default, color=OK, ls="--", lw=1,
               label=f"default ({serial / default:.1f}x)")
    ax.set_xscale("log")
    ax.set_xlabel("chunksize (log)")
    ax.set_ylabel("speedup vs serial")
    ax.legend()
    ax.set_title("ex05 chunksize U-shape\ntiny=IPC cost, huge=idle CPUs")
    save(fig, str(HERE / "ex05_chunksize" / "x.py"))


def chart_ex06(_):
    m = load("ex06_queue_overhead")
    serial, rows = m.measure()
    labels = ["serial\n(no queue)"] + [f"{w} wkr\nqueue" for w, _ in rows]
    vals = [serial] + [t for _, t in rows]
    colors = [GOOD] + [RED] * len(rows)
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    bars = ax.bar(labels, vals, color=colors)
    _barlabels(ax, bars, fmt="{:.2f}s", dy=1.02)
    ax.set_ylabel("seconds")
    ax.set_title("ex06 Queue overhead\nlight work: every queue loses to serial")
    save(fig, str(HERE / "ex06_queue_overhead" / "x.py"))


def chart_ex07(_):
    m = load("ex07_ipc_flag")
    out = m.measure()
    # Mean nonprime time and mean prime time per approach.
    nonprime = ["large nonprime 1", "large nonprime 2"]
    prime = ["prime 1", "prime 2"]
    names = list(out.keys())   # follows active_approaches(); includes Redis if it ran
    np_mean = [sum(out[n][k] for k in nonprime) / 2 for n in names]
    pr_mean = [sum(out[n][k] for k in prime) / 2 for n in names]
    fig, ax = plt.subplots(figsize=(5.6, 3.8))
    x = range(len(names))
    w = 0.4
    ax.bar([i - w / 2 for i in x], np_mean, w, color=WARN, label="big nonprime (can early-exit)")
    ax.bar([i + w / 2 for i in x], pr_mean, w, color=VIO, label="prime (no early-exit)")
    ax.set_yscale("log")
    ax.set_xticks(list(x))
    ax.set_xticklabels([n.replace(" ", "\n") for n in names], fontsize=7)
    ax.set_ylabel("seconds (log)")
    ax.legend(fontsize=7)
    ax.set_title("ex07 IPC flags: early-exit helps nonprimes,\nhurts primes; mmap claws it back")
    save(fig, str(HERE / "ex07_ipc_flag" / "x.py"))


def chart_ex08(_):
    m = load("ex08_shared_numpy")
    elapsed, pid_counts = m.run()
    one = m.main_nparray.nbytes / 1e6   # MB
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    bars = ax.bar(["shared\n(1 copy)", f"copy per worker\n({m.NBR_OF_PROCESSES}x)"],
                  [one, one * m.NBR_OF_PROCESSES], color=[GOOD, RED])
    _barlabels(ax, bars, fmt="{:.0f} MB")
    ax.set_ylabel("RAM (MB)")
    ax.set_title(f"ex08 shared numpy array\nfilled by {m.NBR_OF_PROCESSES} procs in "
                 f"{elapsed:.2f}s, no copy")
    save(fig, str(HERE / "ex08_shared_numpy" / "x.py"))


def chart_ex09(_):
    m = load("ex09_locking")
    out = m.measure()
    names = list(out.keys())
    counts = [out[n][0] for n in names]
    colors = [RED if c != m.EXPECTED else GOOD for c in counts]
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    bars = ax.bar([n.replace(" ", "\n") for n in names], counts, color=colors)
    ax.axhline(m.EXPECTED, color=SLOW, ls="--", lw=1, label=f"expected {m.EXPECTED:,}")
    _barlabels(ax, bars, fmt="{:.0f}", dy=1.02)
    ax.set_ylabel("final count")
    ax.legend()
    ax.set_title("ex09 locking a Value\nno lock loses increments; lock fixes it")
    save(fig, str(HERE / "ex09_locking" / "x.py"))


CHARTS = {
    "ex01": chart_ex01, "ex02": chart_ex02, "ex03": chart_ex03, "ex04": chart_ex04,
    "ex05": chart_ex05, "ex06": chart_ex06, "ex07": chart_ex07, "ex08": chart_ex08,
    "ex09": chart_ex09,
}

FOLDERS = {
    "ex01": "ex01_pi_threads_vs_processes", "ex02": "ex02_process_scaling",
    "ex03": "ex03_pi_numpy", "ex04": "ex04_joblib", "ex05": "ex05_chunksize",
    "ex06": "ex06_queue_overhead", "ex07": "ex07_ipc_flag",
    "ex08": "ex08_shared_numpy", "ex09": "ex09_locking",
}


def build_dashboard():
    import matplotlib.image as mpimg
    fig, axes = plt.subplots(3, 3, figsize=(18, 12))
    for ax, (key, folder) in zip(axes.flat, FOLDERS.items()):
        png = HERE / folder / "chart.png"
        ax.axis("off")
        if png.exists():
            ax.imshow(mpimg.imread(png))
    fig.suptitle("Chapter 10 — Multiprocessing: exercise dashboard",
                 fontsize=16, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    out = HERE / "exercises_dashboard.png"
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {out}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="run a single exercise, e.g. ex05")
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
