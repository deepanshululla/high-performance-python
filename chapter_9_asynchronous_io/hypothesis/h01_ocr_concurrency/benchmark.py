"""h01 — Is there an optimal number of concurrent OCR calls for the render->OCR->analyze pipeline?

HYPOTHESIS: Raising the OCR concurrency speeds the pipeline up only until the *other* bottleneck
takes over. Here each page also carries a heavy, GIL-holding CPU analysis (~3s), so once enough
OCR calls overlap to hide most of the I/O, the serialized CPU work becomes the floor and more
concurrency buys nothing. We predict runtime drops from serial, falls steeply through low
concurrency, then flattens — a per-pipeline echo of ex03's diminishing returns, but with the
plateau set by CPU contention rather than event-loop dispatch.

PREDICTED OUTCOME: total time decreases with concurrency up to a knee (around the point where
overlapped OCR ≈ total serial CPU) and then plateaus; it does *not* keep falling toward
OCR_per_page, because the CPU stages cannot overlap under the GIL.

This calls a real `claude -p` per page per configuration, so the numbers are single-run and
nondeterministic; the *shape* (a knee, then a plateau) is the claim, not the exact seconds.

    .venv/bin/python chapter_9_asynchronous_io/hypothesis/h01_ocr_concurrency/benchmark.py --pages 6
"""
import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))   # repo root
sys.path.insert(0, str(HERE.parents[1]))   # chapter dir

import _ocr  # noqa: E402

PDF = HERE.parents[1] / "ex09_ocr_pipeline" / "sample.pdf"
RENDER_DIR = HERE / "pages"
RESULTS = HERE / "results.json"
CHART = HERE / "h01_ocr_concurrency.png"
CONCURRENCIES = [1, 2, 4, 8]


def plot():
    """Draw the chart from the captured results.json (no re-run — OCR calls are costly)."""
    from vizutil import plt, setup, save, COLORS
    data = json.loads(RESULTS.read_text())
    setup()
    fig, ax = plt.subplots(figsize=(5.2, 4.0))
    xs = [s["concurrency"] for s in data["sweep"]]
    ys = [s["total"] for s in data["sweep"]]
    ax.plot(xs, ys, "o-", color=COLORS["teal"], lw=2, label="async pipeline")
    ax.axhline(data["serial_total"], color=COLORS["amber"], ls="--", lw=1.2,
               label=f"serial ({data['serial_total']:.0f}s)")
    ax.axhline(data["serial_cpu"], color=COLORS["gray"], ls=":", lw=1.4,
               label=f"serial-CPU floor ({data['serial_cpu']:.0f}s)")
    ax.scatter([data["knee_concurrency"]],
               [next(s["total"] for s in data["sweep"] if s["concurrency"] == data["knee_concurrency"])],
               s=160, facecolors="none", edgecolors=COLORS["red"], lw=2, zorder=5,
               label=f"knee @ c={data['knee_concurrency']}")
    ax.set_xscale("log", base=2)
    ax.set_xticks(xs)
    ax.set_xticklabels([str(x) for x in xs])
    ax.set_xlabel("OCR concurrency")
    ax.set_ylabel("seconds")
    ax.set_ylim(0, data["serial_total"] * 1.1)
    ax.set_title(f"h01 OCR concurrency — {data['verdict']}")
    ax.legend(fontsize=8)
    save(fig, str(HERE / "x.py"), name=CHART.name,
         subtitle="VERDICT: more concurrency saturates once OCR is hidden and GIL-bound CPU is the floor")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=6)
    parser.add_argument("--plot", action="store_true", help="redraw chart from results.json")
    args = parser.parse_args()
    if args.plot:
        plot()
        return
    pages = list(range(args.pages))

    print(f"h01: OCR concurrency sweep over {args.pages} pages\n")
    serial = _ocr.run_serial(PDF, pages, RENDER_DIR)
    cpu_total = serial["stages"]["analyze"] + serial["stages"]["render"]
    print(f"  serial          : {serial['total']:5.1f}s  "
          f"(OCR {serial['stages']['ocr']:.1f}s + CPU {cpu_total:.1f}s)")

    sweep = []
    for c in CONCURRENCIES:
        r = _ocr.run_async(PDF, pages, RENDER_DIR, concurrency=c)
        sweep.append({"concurrency": c, "total": r["total"]})
        print(f"  async c={c:<2}        : {r['total']:5.1f}s  "
              f"({serial['total'] / r['total']:.2f}x vs serial)")

    best = min(sweep, key=lambda s: s["total"])
    # The knee: first concurrency within 5% of the best time.
    knee = next(s["concurrency"] for s in sweep if s["total"] <= best["total"] * 1.05)
    plateaus = best["total"] > cpu_total * 0.8   # best time is floored near the serial CPU sum
    verdict = "CONFIRMED" if (knee < CONCURRENCIES[-1] and plateaus) else "OVERTURNED"

    out = {
        "pdf": PDF.name, "n_pages": args.pages, "model": _ocr.OCR_MODEL,
        "serial_total": serial["total"], "serial_ocr": serial["stages"]["ocr"],
        "serial_cpu": cpu_total, "sweep": sweep,
        "knee_concurrency": knee, "best": best, "verdict": verdict,
    }
    RESULTS.write_text(json.dumps(out, indent=2))
    print(f"\n  knee at concurrency {knee}; best {best['total']:.1f}s vs serial-CPU floor "
          f"{cpu_total:.1f}s")
    print(f"  VERDICT: {verdict} — speedup saturates once OCR is hidden and CPU becomes the floor")
    print(f"  wrote {RESULTS.name}")


if __name__ == "__main__":
    main()
