"""Generate a chart for every Chapter 9 exercise and tile them into a dashboard.

Each exercise lives in its own folder (chapter_9_asynchronous_io/exNN_name/exNN_name.py).
This driver imports each module by path and REUSES its measurement functions against a single
shared delay-server, so the charts show the same numbers the scripts print. It writes
`chart.png` into each folder, then assembles `exercises_dashboard.png` here.

Run: .venv/bin/python chapter_9_asynchronous_io/visualize_exercises.py
     .venv/bin/python chapter_9_asynchronous_io/visualize_exercises.py --only ex03
"""
import argparse
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0]))   # repo root -> vizutil, perf
sys.path.insert(0, str(HERE))               # chapter dir -> _server, _workload

from vizutil import plt, setup, save, COLORS  # noqa: E402
from _server import running_server  # noqa: E402
from _workload import (  # noqa: E402
    N_REQUESTS, N_HASHES, URL_DELAY_MS, DEFAULT_DIFFICULTY,
)

GOOD, OK, SLOW, WARN, VIO = (
    COLORS["teal"], COLORS["blue"], COLORS["gray"], COLORS["amber"], COLORS["violet"],
)


def load(folder):
    d = HERE / folder
    sys.path.insert(0, str(d))
    spec = importlib.util.spec_from_file_location(folder, d / f"{folder}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _barlabels(ax, bars, fmt="{:.2f}", dy=1.01):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() * dy,
                fmt.format(b.get_height()), ha="center", va="bottom", fontsize=9)


# --- one chart function per exercise; each measures, plots, and saves into its folder -------

def chart_ex01(base):
    m = load("ex01_serial_crawler")
    url = f"{base}/get?delay={URL_DELAY_MS}&name=serial"
    _, elapsed = m.measure(url, N_REQUESTS)
    ideal = N_REQUESTS * URL_DELAY_MS / 1000
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    bars = ax.bar(["ideal floor\n(N x delay)", "serial\nmeasured"], [ideal, elapsed],
                  color=[SLOW, WARN])
    _barlabels(ax, bars, fmt="{:.1f}s")
    ax.set_ylabel("seconds")
    ax.set_title(f"ex01 serial crawler\n{N_REQUESTS} requests @ {URL_DELAY_MS}ms")
    save(fig, str(HERE / "ex01_serial_crawler" / "x.py"))


def chart_ex02(base):
    m = load("ex02_aiohttp_crawler")
    serial = load("ex01_serial_crawler")
    url = f"{base}/get?delay={URL_DELAY_MS}&name=crawl"
    _, serial_t = serial.measure(url, N_REQUESTS)
    _, async_t = m.measure_async(url, N_REQUESTS)
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    bars = ax.bar(["serial", "async\n(aiohttp)"], [serial_t, async_t], color=[WARN, GOOD])
    ax.set_yscale("log")
    _barlabels(ax, bars, fmt="{:.2f}s")
    ax.set_ylabel("seconds (log)")
    ax.set_title(f"ex02 async crawler\n{serial_t / async_t:.0f}x speedup")
    save(fig, str(HERE / "ex02_aiohttp_crawler" / "x.py"))


def chart_ex03(base):
    m = load("ex03_concurrency_sweep")
    data = m.sweep(base)
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    colors = {m.DELAYS_MS[0]: WARN, m.DELAYS_MS[1]: GOOD}
    for delay, row in data.items():
        xs = [lim for lim, _ in row]
        ys = [e for _, e in row]
        ax.plot(xs, ys, "o-", color=colors.get(delay, OK), label=f"{delay}ms delay")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("concurrency limit")
    ax.set_ylabel("seconds (log)")
    ax.axvline(250, color=SLOW, ls="--", lw=1)
    ax.text(250, ax.get_ylim()[1], " ~250 knee", color=SLOW, fontsize=8, va="top")
    ax.legend()
    ax.set_title("ex03 concurrency sweep")
    save(fig, str(HERE / "ex03_concurrency_sweep" / "x.py"))


def chart_ex04(base):
    m = load("ex04_lazy_scheduling")
    lazy = m.run(eager=False)
    eager = m.run(eager=True)
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    # Plot each event as a dot along its log position, two rows (lazy / eager).
    kinds = {"create": SLOW, "loop-end": WARN, "run": GOOD, "resume": OK}
    for row, log in ((1, lazy), (0, eager)):
        for pos, (kind, _) in enumerate(log):
            ax.scatter(pos, row, color=kinds.get(kind, OK), s=60, zorder=3)
    # Mark loop-end with a vertical tick per row.
    for row, log in ((1, lazy), (0, eager)):
        le = next(p for p, (k, _) in enumerate(log) if k == "loop-end")
        ax.scatter(le, row, color=WARN, s=120, marker="|", zorder=4)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["eager", "lazy"])
    ax.set_xlabel("event order ->")
    ax.set_title("ex04 when tasks run\n(green=body; amber=loop-end)")
    handles = [plt.Line2D([0], [0], marker="o", ls="", color=c, label=k)
               for k, c in kinds.items()]
    ax.legend(handles=handles, fontsize=7, ncol=2)
    ax.set_ylim(-0.5, 1.5)
    save(fig, str(HERE / "ex04_lazy_scheduling" / "x.py"))


def chart_ex05(base):
    m = load("ex05_serial_cpu_io")
    url = f"{base}/add?delay={URL_DELAY_MS}&name=serial-save"
    total, cpu_only = m.measure(url, N_HASHES, DEFAULT_DIFFICULTY)
    io = total - cpu_only
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    ax.bar(["serial"], [cpu_only], color=GOOD, label="CPU")
    ax.bar(["serial"], [io], bottom=[cpu_only], color=WARN, label="I/O wait")
    ax.text(0, total * 1.01, f"{total:.1f}s\n({100 * io / total:.0f}% I/O)",
            ha="center", fontsize=9)
    ax.set_ylabel("seconds")
    ax.set_title(f"ex05 serial CPU+I/O\n{N_HASHES} hashes, diff {DEFAULT_DIFFICULTY}")
    ax.legend()
    save(fig, str(HERE / "ex05_serial_cpu_io" / "x.py"))


def chart_ex06(base):
    m = load("ex06_batched_pipeline")
    serial = load("ex05_serial_cpu_io")
    url = f"{base}/add?delay={URL_DELAY_MS}&name=batched"
    serial_total, _ = serial.measure(url, N_HASHES, DEFAULT_DIFFICULTY)
    batched = m.measure(url, N_HASHES, DEFAULT_DIFFICULTY, batch_size=100)
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    bars = ax.bar(["serial", "batched\n(pipeline)"], [serial_total, batched], color=[WARN, OK])
    _barlabels(ax, bars, fmt="{:.2f}s")
    ax.set_ylabel("seconds")
    ax.set_title(f"ex06 batched\n{serial_total / batched:.1f}x speedup")
    save(fig, str(HERE / "ex06_batched_pipeline" / "x.py"))


def chart_ex07(base):
    m = load("ex07_full_async")
    serial = load("ex05_serial_cpu_io")
    batch = load("ex06_batched_pipeline")
    url = f"{base}/add?delay={URL_DELAY_MS}&name=full"
    serial_total, cpu_only = serial.measure(url, N_HASHES, DEFAULT_DIFFICULTY)
    batched = batch.measure(url, N_HASHES, DEFAULT_DIFFICULTY, batch_size=100)
    full = m.measure(url, N_HASHES, DEFAULT_DIFFICULTY, yield_each=True)
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    bars = ax.bar(["serial", "batched", "full\nasync", "CPU\nfloor"],
                  [serial_total, batched, full, cpu_only],
                  color=[WARN, OK, GOOD, SLOW])
    _barlabels(ax, bars, fmt="{:.2f}s")
    ax.set_ylabel("seconds")
    ax.set_title(f"ex07 full async\nI/O hidden under CPU ({serial_total / full:.1f}x)")
    save(fig, str(HERE / "ex07_full_async" / "x.py"))


def chart_ex08(base):
    m = load("ex08_sleep_zero")
    cpu_only, rows = m.sweep(base)
    labels = ["never" if k == 0 else f"{k}" for k, _ in rows]
    overs = [e - cpu_only for _, e in rows]
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    colors = [GOOD if o < 0.15 else (WARN if o < 0.4 else COLORS["red"]) for o in overs]
    bars = ax.bar(labels, overs, color=colors)
    _barlabels(ax, bars, fmt="{:+.2f}", dy=1.02)
    ax.set_xlabel("yield every K iterations")
    ax.set_ylabel("seconds over CPU floor")
    ax.set_title(f"ex08 sleep(0) cadence\nstarvation drain (conn limit {m.CONN_LIMIT})")
    save(fig, str(HERE / "ex08_sleep_zero" / "x.py"))


CHARTS = {
    "ex01": chart_ex01, "ex02": chart_ex02, "ex03": chart_ex03, "ex04": chart_ex04,
    "ex05": chart_ex05, "ex06": chart_ex06, "ex07": chart_ex07, "ex08": chart_ex08,
}


def build_dashboard():
    """Tile the eight per-folder chart.png files into one dashboard image."""
    import matplotlib.image as mpimg
    folders = {
        "ex01": "ex01_serial_crawler", "ex02": "ex02_aiohttp_crawler",
        "ex03": "ex03_concurrency_sweep", "ex04": "ex04_lazy_scheduling",
        "ex05": "ex05_serial_cpu_io", "ex06": "ex06_batched_pipeline",
        "ex07": "ex07_full_async", "ex08": "ex08_sleep_zero",
    }
    fig, axes = plt.subplots(2, 4, figsize=(18, 8))
    for ax, (key, folder) in zip(axes.flat, folders.items()):
        png = HERE / folder / "chart.png"
        ax.axis("off")
        if png.exists():
            ax.imshow(mpimg.imread(png))
    fig.suptitle("Chapter 9 — Asynchronous I/O: exercise dashboard",
                 fontsize=16, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    out = HERE / "exercises_dashboard.png"
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {out}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="run a single exercise, e.g. ex03")
    parser.add_argument("--no-dashboard", action="store_true")
    args = parser.parse_args()
    setup()
    todo = {args.only: CHARTS[args.only]} if args.only else CHARTS
    with running_server() as base:
        for key, fn in todo.items():
            print(f"== {key} ==")
            fn(base)
    if not args.only and not args.no_dashboard:
        build_dashboard()


if __name__ == "__main__":
    main()
