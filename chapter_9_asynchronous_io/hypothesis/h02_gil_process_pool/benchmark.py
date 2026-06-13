"""h02 — Does a process pool help once the CPU stages are heavy? (The GIL question.)

HYPOTHESIS: Pure asyncio overlaps each page's OCR I/O with *other* pages' work, but it cannot
overlap the two CPU stages (render, analyze) of different pages, because pure-Python code holds
the GIL — only one coroutine's CPU work runs at a time, and while it runs the event loop is
blocked. So when the CPU stages are heavy (here ~3s of GIL-bound edit-distance analysis per
page), async-only is floored by the *sum* of all CPU work. Offloading render+analyze to a
`ProcessPoolExecutor` runs them in separate interpreters with their own GILs, truly in parallel,
while the event loop stays free to juggle the OCR subprocesses.

PREDICTED OUTCOME (CONFIRMED): async + process pool beats async-only by roughly the CPU work it
parallelizes — the async-only run is limited by serial CPU, the pooled run by max(overlapped OCR,
CPU / workers). Both beat serial. This is the concrete reason the book says you eventually need
multiprocessing: asyncio hides I/O behind I/O, but not CPU behind CPU.

Real `claude -p` per page; single-run, nondeterministic numbers — the ordering is the claim.

    .venv/bin/python chapter_9_asynchronous_io/hypothesis/h02_gil_process_pool/benchmark.py --pages 6
"""
import argparse
import asyncio
import json
import os
import pathlib
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))   # repo root
sys.path.insert(0, str(HERE.parents[1]))   # chapter dir

import _ocr  # noqa: E402

PDF = HERE.parents[1] / "ex09_ocr_pipeline" / "sample.pdf"
RENDER_DIR = HERE / "pages"
RESULTS = HERE / "results.json"
CHART = HERE / "h02_gil_process_pool.png"
CONCURRENCY = 4
WORKERS = min(4, os.cpu_count() or 4)


def plot():
    """Draw the chart from the captured results.json (no re-run — OCR calls are costly)."""
    from vizutil import plt, setup, save, COLORS
    d = json.loads(RESULTS.read_text())
    setup()
    fig, ax = plt.subplots(figsize=(5.2, 4.0))
    labels = ["serial", "async-only\n(GIL CPU)", "async +\nprocess pool"]
    vals = [d["serial_total"], d["async_inline"], d["async_pooled"]]
    colors = [COLORS["amber"], COLORS["blue"], COLORS["teal"]]
    bars = ax.bar(labels, vals, color=colors)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.01, f"{v:.0f}s",
                ha="center", va="bottom", fontsize=10)
    ax.axhline(d["serial_cpu"], color=COLORS["gray"], ls=":", lw=1.4,
               label=f"serial-CPU sum ({d['serial_cpu']:.0f}s)")
    ax.set_ylabel("seconds")
    ax.set_ylim(0, d["serial_total"] * 1.12)
    ax.set_title(f"h02 GIL / process pool — {d['verdict']}")
    ax.legend(fontsize=8)
    save(fig, str(HERE / "x.py"), name=CHART.name,
         subtitle=f"VERDICT: {d['verdict']} — process pool {d['pool_gain']:.2f}x over async-only "
                  f"by parallelizing GIL-bound CPU")


async def _handle_pooled(pdf, idx, render_dir, pool, sem):
    """render (CPU, in a worker process) -> OCR (I/O, in the loop) -> analyze (CPU, in a worker)."""
    loop = asyncio.get_running_loop()
    png = await loop.run_in_executor(pool, _ocr.render_page, pdf, idx, render_dir)
    async with sem:
        text = await _ocr.ocr_page_async(png)
        await asyncio.sleep(0)
    stats = await loop.run_in_executor(pool, _ocr.analyze_text, text)
    return {"page": idx, "stats": stats}


async def _run_pooled(pdf, pages, render_dir, concurrency, workers):
    sem = asyncio.Semaphore(concurrency)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        tasks = [_handle_pooled(pdf, i, render_dir, pool, sem) for i in pages]
        return await asyncio.gather(*tasks)


def run_pooled(pdf, pages, render_dir, concurrency=CONCURRENCY, workers=WORKERS):
    t0 = time.perf_counter()
    asyncio.run(_run_pooled(pdf, pages, render_dir, concurrency, workers))
    return time.perf_counter() - t0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=6)
    parser.add_argument("--plot", action="store_true", help="redraw chart from results.json")
    args = parser.parse_args()
    if args.plot:
        plot()
        return
    pages = list(range(args.pages))

    print(f"h02: GIL / process-pool, {args.pages} pages, OCR concurrency {CONCURRENCY}, "
          f"{WORKERS} CPU workers\n")

    serial = _ocr.run_serial(PDF, pages, RENDER_DIR)
    cpu_total = serial["stages"]["analyze"] + serial["stages"]["render"]
    print(f"  serial               : {serial['total']:5.1f}s  "
          f"(OCR {serial['stages']['ocr']:.1f}s + CPU {cpu_total:.1f}s)")

    inline = _ocr.run_async(PDF, pages, RENDER_DIR, concurrency=CONCURRENCY)
    print(f"  async-only (GIL CPU) : {inline['total']:5.1f}s  "
          f"({serial['total'] / inline['total']:.2f}x vs serial)")

    pooled = run_pooled(PDF, pages, RENDER_DIR)
    print(f"  async + process pool : {pooled:5.1f}s  "
          f"({serial['total'] / pooled:.2f}x vs serial)")

    gain = inline["total"] / pooled
    verdict = "CONFIRMED" if gain > 1.10 else "OVERTURNED"
    out = {
        "pdf": PDF.name, "n_pages": args.pages, "model": _ocr.OCR_MODEL,
        "concurrency": CONCURRENCY, "workers": WORKERS,
        "serial_total": serial["total"], "serial_cpu": cpu_total,
        "async_inline": inline["total"], "async_pooled": pooled,
        "pool_gain": gain, "verdict": verdict,
    }
    RESULTS.write_text(json.dumps(out, indent=2))
    print(f"\n  process pool vs async-only: {gain:.2f}x")
    print(f"  VERDICT: {verdict} — "
          + ("the pool parallelizes the GIL-bound CPU stages asyncio could not"
             if verdict == "CONFIRMED"
             else "CPU was too small a share for the pool to matter"))
    print(f"  wrote {RESULTS.name}")


if __name__ == "__main__":
    main()
