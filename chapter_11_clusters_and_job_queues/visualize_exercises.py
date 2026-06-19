"""Generate a chart for every Chapter 11 exercise and tile them into a dashboard.

Each exercise lives in its own folder (chapter_11_clusters_and_job_queues/exNN_name/exNN_name.py).
This driver imports each module by path and REUSES its measurement functions, so the charts show the
same numbers the scripts print. It writes `chart.png` into each folder, then assembles
`exercises_dashboard.png` here.

Several exercises re-measure expensively: ex01/ex02/ex03 each start an IPython cluster (~7 s of
startup apiece), ex04-ex07 each start and remove their own ephemeral Redis container, and ex09
builds/runs a Docker container. All of these need Docker running; any chart that errors is reported
and skipped rather than crashing the whole run, and `--only exNN` regenerates a single chart while
iterating.

Run: .venv/bin/python chapter_11_clusters_and_job_queues/visualize_exercises.py
     .venv/bin/python chapter_11_clusters_and_job_queues/visualize_exercises.py --only ex06
"""
import argparse
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0]))   # repo root -> vizutil, perf
sys.path.insert(0, str(HERE))               # chapter dir -> _cluster, _ipp

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
    # Register before exec so a forked Pool/Process worker (ex04, ex05) can resolve
    # "<folder>.consumer" back to the same object.
    sys.modules[folder] = mod
    spec.loader.exec_module(mod)
    return mod


def _barlabels(ax, bars, fmt="{:.2f}", dy=1.01):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() * dy,
                fmt.format(b.get_height()), ha="center", va="bottom", fontsize=9)


def chart_ex01(_):
    m = load("ex01_ipython_pi")
    r = m.measure()
    fig, ax = plt.subplots(figsize=(4.4, 3.6))
    bars = ax.bar(["serial", "cluster\n(warm)"], [r["serial"], r["cluster"]],
                  color=[SLOW, GOOD])
    ax.bar(["cluster\n(warm)"], [r["startup"]], bottom=[r["cluster"]],
           color=WARN, alpha=0.85, label="startup (one-time)")
    _barlabels(ax, bars, fmt="{:.1f}s")
    ax.set_ylabel("seconds")
    ax.legend(fontsize=8)
    ax.set_title(f"ex01 IPython pi, {m.N_ENGINES} engines\n"
                 f"compute {r['serial']/r['cluster']:.1f}x, but startup {r['startup']/r['cluster']:.1f}x the compute")
    save(fig, str(HERE / "ex01_ipython_pi" / "x.py"))


def chart_ex02(_):
    m = load("ex02_push_pull_latency")
    r = m.measure()
    fig, (axp, axb) = plt.subplots(1, 2, figsize=(8.6, 3.6))
    xs = [nb / 1e6 for nb, _ in r["push"]]
    ys = [dt * 1e3 for _, dt in r["push"]]
    axp.plot(xs, ys, "o-", color=OK)
    axp.set_xscale("log"); axp.set_yscale("log")
    axp.axhline(r["lat_all_ms"], color=SLOW, ls="--", lw=1,
                label=f"latency floor {r['lat_all_ms']:.0f}ms")
    axp.set_xlabel("payload (MB, log)"); axp.set_ylabel("push ms (log)")
    axp.legend(fontsize=8); axp.set_title("ex02 push: latency- then\nbandwidth-bound")
    bars = axb.bar(["chatty\n(N calls)", "batched\n(1 call)"], [r["tiny_s"], r["batched_s"]],
                   color=[RED, GOOD])
    axb.set_yscale("log"); _barlabels(axb, bars, fmt="{:.2f}s", dy=1.05)
    axb.set_ylabel("seconds (log)")
    axb.set_title(f"{m.TINY_CALLS} trivial jobs\nbatching {r['tiny_s']/r['batched_s']:.0f}x faster")
    save(fig, str(HERE / "ex02_push_pull_latency" / "x.py"))


def chart_ex03(_):
    m = load("ex03_direct_vs_loadbalanced")
    r = m.measure()
    fig, (axt, axl) = plt.subplots(1, 2, figsize=(8.6, 3.6))
    bars = axt.bar(["direct\n(static)", "load-bal\n(on-demand)"], [r["direct_s"], r["lb_s"]],
                   color=[RED, GOOD])
    _barlabels(axt, bars, fmt="{:.2f}s")
    axt.set_ylabel("seconds")
    axt.set_title(f"ex03 uneven work\nload-bal {r['direct_s']/r['lb_s']:.2f}x faster")
    dload = sorted((v / 1e6 for v in r["direct_load"].values()), reverse=True)
    lload = sorted((v / 1e6 for v in r["lb_load"].values()), reverse=True)
    x = range(len(dload)); w = 0.4
    axl.bar([i - w/2 for i in x], dload, w, color=RED, label="direct")
    axl.bar([i + w/2 for i in x], lload, w, color=GOOD, label="load-bal")
    axl.set_xlabel("engine (sorted)"); axl.set_ylabel("darts handled (M)")
    axl.legend(fontsize=8); axl.set_title("per-engine load\nstatic split = stragglers")
    save(fig, str(HERE / "ex03_direct_vs_loadbalanced" / "x.py"))


def chart_ex04(_):
    m = load("ex04_redis_work_queue")
    rows = m.measure()
    base = rows[0][1]
    xs = [c for c, _ in rows]
    speed = [base / t for _, t in rows]
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    ax.plot(xs, speed, "o-", color=GOOD, label="measured")
    ax.plot(xs, xs, "--", color=SLOW, lw=1, label="ideal (linear)")
    ax.axvline(8, color=VIO, ls=":", lw=1)
    ax.text(8, 1, " 8 P-cores", color=VIO, fontsize=8, rotation=90, va="bottom")
    ax.set_xlabel("consumers"); ax.set_ylabel("speedup vs 1 consumer")
    ax.legend(fontsize=8)
    ax.set_title(f"ex04 Redis work queue\npeak {max(speed):.1f}x — scale by adding consumers")
    save(fig, str(HERE / "ex04_redis_work_queue" / "x.py"))


def chart_ex05(_):
    m = load("ex05_queue_buffer")
    r = m.measure()
    fig, ax = plt.subplots(figsize=(4.8, 3.6))
    for name, color in [("burst", RED), ("steady", GOOD)]:
        ts = [t for t, _ in r[name]["samples"]]
        ds = [d for _, d in r[name]["samples"]]
        ax.plot(ts, ds, "-", color=color, lw=1.6,
                label=f"{name} (peak {r[name]['peak']})")
    ax.set_xlabel("time (s)"); ax.set_ylabel("queue depth (jobs)")
    ax.legend(fontsize=8)
    ax.set_title("ex05 queue as buffer\nburst inflates depth, not finish time")
    save(fig, str(HERE / "ex05_queue_buffer" / "x.py"))


def chart_ex06(_):
    m = load("ex06_pubsub_vs_consumer_group")
    r = m.measure()
    fig, ax = plt.subplots(figsize=(4.8, 3.6))
    k = len(r["fanout"]); x = range(k); w = 0.4
    ax.bar([i - w/2 for i in x], r["fanout"], w, color=VIO, label="pub/sub fan-out")
    ax.bar([i + w/2 for i in x], r["group"], w, color=GOOD, label="consumer group")
    ax.axhline(m.N_MESSAGES, color=SLOW, ls="--", lw=1, label=f"one pass ({m.N_MESSAGES})")
    ax.set_xlabel("consumer"); ax.set_ylabel("messages received")
    ax.set_xticks(list(x)); ax.legend(fontsize=8)
    ax.set_title("ex06 fan-out vs consumer group\neveryone-gets-all vs split one pass")
    save(fig, str(HERE / "ex06_pubsub_vs_consumer_group" / "x.py"))


def chart_ex07(_):
    m = load("ex07_delivery_guarantees")
    r = m.measure()
    amo, alo = r["at_most_once"], r["at_least_once"]
    fig, ax = plt.subplots(figsize=(4.8, 3.6))
    labels = ["at-most-once\n(list+LPOP)", "at-least-once\n(stream+XACK)"]
    once = [amo["unique"], alo["unique"]]
    dup = [amo["duplicated"], alo["duplicated"]]
    b1 = ax.bar(labels, once, color=GOOD, label="processed once")
    ax.bar(labels, dup, bottom=once, color=WARN, label="duplicated")
    # mark losses as the gap up to N
    for i, s in enumerate([amo, alo]):
        if s["lost"]:
            ax.bar(labels[i], s["lost"], bottom=m.N_MESSAGES - s["lost"], color=RED,
                   label="lost" if i == 0 else None)
    ax.axhline(m.N_MESSAGES, color=SLOW, ls="--", lw=1, label=f"all {m.N_MESSAGES}")
    _barlabels(ax, b1, fmt="{:.0f}", dy=1.0)
    ax.set_ylabel("messages"); ax.legend(fontsize=7)
    ax.set_title("ex07 delivery guarantees\nlose in-flight vs duplicate on recovery")
    save(fig, str(HERE / "ex07_delivery_guarantees" / "x.py"))


def chart_ex08(_):
    m = load("ex08_message_serialization")
    out = m.measure()
    names = list(out.keys())
    fig, (axs, axt) = plt.subplots(1, 2, figsize=(8.6, 3.6))
    colors = [OK if n == "json" else GOOD if n == "msgpack" else VIO for n in names]
    b1 = axs.bar(names, [out[n]["size"] for n in names], color=colors)
    _barlabels(axs, b1, fmt="{:.0f}B")
    axs.set_ylabel("serialized size (bytes)"); axs.set_title("ex08 size")
    rt = [out[n]["encode_us"] + out[n]["decode_us"] for n in names]
    b2 = axt.bar(names, rt, color=colors)
    _barlabels(axt, b2, fmt="{:.1f}us")
    axt.set_ylabel("round-trip (us)"); axt.set_title("encode+decode time")
    fig.suptitle("JSON: readable but slower & larger; msgpack: compact & portable",
                 fontsize=9, y=1.02)
    save(fig, str(HERE / "ex08_message_serialization" / "x.py"))


def chart_ex09(_):
    m = load("ex09_docker_overhead")
    r = m.measure()
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    if r is None:
        ax.text(0.5, 0.5, "Docker unavailable\n(exercise skipped)", ha="center", va="center")
        ax.axis("off")
        save(fig, str(HERE / "ex09_docker_overhead" / "x.py"))
        return
    bars = ax.bar(["host", "container"], [r["host"] * 1000, r["container"] * 1000],
                  color=[GOOD, RED])
    ax.bar(["container"], [r["startup"] * 1000], bottom=[r["container"] * 1000],
           color=WARN, alpha=0.85, label="startup (per run)")
    ax.axhline(r["host"] * 1000, color=SLOW, ls="--", lw=1, label="host (Linux ~0 overhead)")
    _barlabels(ax, bars, fmt="{:.0f}ms")
    ax.set_ylabel("compute (ms)"); ax.legend(fontsize=8)
    ax.set_title(f"ex09 Docker on macOS\ncontainer {r['container']/r['host']:.1f}x slower (VM)")
    save(fig, str(HERE / "ex09_docker_overhead" / "x.py"))


CHARTS = {
    "ex01": chart_ex01, "ex02": chart_ex02, "ex03": chart_ex03, "ex04": chart_ex04,
    "ex05": chart_ex05, "ex06": chart_ex06, "ex07": chart_ex07, "ex08": chart_ex08,
    "ex09": chart_ex09,
}

FOLDERS = {
    "ex01": "ex01_ipython_pi", "ex02": "ex02_push_pull_latency",
    "ex03": "ex03_direct_vs_loadbalanced", "ex04": "ex04_redis_work_queue",
    "ex05": "ex05_queue_buffer", "ex06": "ex06_pubsub_vs_consumer_group",
    "ex07": "ex07_delivery_guarantees", "ex08": "ex08_message_serialization",
    "ex09": "ex09_docker_overhead",
}


def build_dashboard():
    import matplotlib.image as mpimg
    fig, axes = plt.subplots(3, 3, figsize=(18, 12))
    for ax, (key, folder) in zip(axes.flat, FOLDERS.items()):
        png = HERE / folder / "chart.png"
        ax.axis("off")
        if png.exists():
            ax.imshow(mpimg.imread(png))
    fig.suptitle("Chapter 11 — Clusters and Job Queues: exercise dashboard",
                 fontsize=16, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    out = HERE / "exercises_dashboard.png"
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {out}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="run a single exercise, e.g. ex06")
    parser.add_argument("--no-dashboard", action="store_true")
    args = parser.parse_args()
    setup()
    todo = {args.only: CHARTS[args.only]} if args.only else CHARTS
    for key, fn in todo.items():
        print(f"== {key} ==")
        try:
            fn(None)
        except SystemExit:
            print(f"   [skipped {key}: backing service unavailable — see exercise notes]")
        except Exception as e:  # keep going so one missing service doesn't kill the run
            print(f"   [skipped {key}: {type(e).__name__}: {str(e)[:80]}]")
    if not args.only and not args.no_dashboard:
        build_dashboard()


if __name__ == "__main__":
    main()
