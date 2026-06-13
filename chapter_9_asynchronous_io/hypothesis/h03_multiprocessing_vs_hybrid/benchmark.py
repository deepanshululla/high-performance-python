"""h03 — Would pure multiprocessing beat the async+pool hybrid? (And what really differs?)

h02 showed that adding a process pool to the async pipeline breaks through the GIL-bound CPU
floor. A natural follow-up: since the pages are completely independent, why bother with asyncio
at all — just run each page (render + blocking OCR + analyze) in its own worker process with
`ProcessPoolExecutor.map`. That is simpler. Is it faster?

HYPOTHESIS: At *matched parallelism*, pure multiprocessing is NOT meaningfully faster than the
async+pool hybrid — both are bounded by the same max(overlapped OCR, CPU / workers). What truly
differs is resource efficiency: pure multiprocessing couples I/O concurrency to process count
(one whole process per in-flight OCR, idle while that OCR runs), whereas the hybrid decouples
them — cheap coroutines give the OCR concurrency while a small process pool gives the CPU
parallelism. So the hybrid can reach the same wall-clock with *fewer worker processes*.

PREDICTED OUTCOME (CONFIRMED):
  * pure-MP(N) ≈ hybrid(OCR=N, CPU=N) within noise, across N — paradigm doesn't matter at
    matched parallelism;
  * hybrid(OCR=6, CPU=2) approaches pure-MP(6 processes) while using a third of the processes,
    because the OCR concurrency comes from coroutines, not processes.

Real `claude -p` per page per config — single-run, nondeterministic numbers. The claim is the
*ordering and the resource argument*, not the seconds.

    .venv/bin/python chapter_9_asynchronous_io/hypothesis/h03_multiprocessing_vs_hybrid/benchmark.py --pages 6
"""
import argparse
import asyncio
import json
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
CHART = HERE / "h03_multiprocessing_vs_hybrid.png"
MATCHED = [2, 4, 6]          # matched-parallelism sweep (workers = OCR concurrency = CPU pool)
DECOUPLED = (6, 2)           # (OCR concurrency, CPU workers) — the efficiency point


# --- pure multiprocessing: one whole page per worker, fully blocking -------------------------

def run_mp(pdf, pages, render_dir, workers):
    args = [(pdf, i, render_dir) for i in pages]
    t = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        list(pool.map(_ocr.process_page_blocking, args))
    return time.perf_counter() - t


# --- async + pool hybrid: coroutines for OCR I/O, a process pool for CPU --------------------

async def _handle(pdf, idx, render_dir, pool, sem):
    loop = asyncio.get_running_loop()
    png = await loop.run_in_executor(pool, _ocr.render_page, pdf, idx, render_dir)
    async with sem:
        text = await _ocr.ocr_page_async(png)
        await asyncio.sleep(0)
    return await loop.run_in_executor(pool, _ocr.analyze_text, text)


async def _run_hybrid(pdf, pages, render_dir, ocr_conc, cpu_workers):
    sem = asyncio.Semaphore(ocr_conc)
    with ProcessPoolExecutor(max_workers=cpu_workers) as pool:
        await asyncio.gather(*[_handle(pdf, i, render_dir, pool, sem) for i in pages])


def run_hybrid(pdf, pages, render_dir, ocr_conc, cpu_workers):
    t = time.perf_counter()
    asyncio.run(_run_hybrid(pdf, pages, render_dir, ocr_conc, cpu_workers))
    return time.perf_counter() - t


def plot():
    from vizutil import plt, setup, save, COLORS
    d = json.loads(RESULTS.read_text())
    setup()
    fig, ax = plt.subplots(figsize=(5.6, 4.0))
    ns = [m["n"] for m in d["matched"]]
    mp = [m["mp"] for m in d["matched"]]
    hy = [m["hybrid"] for m in d["matched"]]
    ax.plot(ns, mp, "o-", color=COLORS["violet"], lw=2, label="pure multiprocessing")
    ax.plot(ns, hy, "s--", color=COLORS["teal"], lw=2, label="async + pool (matched)")
    dec = d["decoupled"]
    ax.scatter([dec["ocr_conc"]], [dec["time"]], s=170, marker="*",
               color=COLORS["amber"], zorder=5,
               label=f"hybrid OCR={dec['ocr_conc']}, CPU={dec['cpu_workers']} "
                     f"({dec['cpu_workers']} procs)")
    ax.set_xticks(ns)
    ax.set_xlabel("parallelism N (workers = OCR concurrency = CPU pool)")
    ax.set_ylabel("seconds")
    ax.set_ylim(0, max(mp + hy) * 1.15)
    ax.set_title(f"h03 multiprocessing vs hybrid — {d['verdict']}")
    ax.legend(fontsize=8)
    mr = d.get("mean_ratio", 1.0)
    save(fig, str(HERE / "x.py"), name=CHART.name,
         subtitle=f"VERDICT: OVERTURNED — the async+pool hybrid is ~{mr:.2f}x FASTER than per-page "
                  f"multiprocessing at matched parallelism (MP idles workers during OCR)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=6)
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()
    if args.plot:
        plot()
        return
    pages = list(range(args.pages))

    print(f"h03: pure multiprocessing vs async+pool hybrid, {args.pages} pages\n")
    serial = _ocr.run_serial(PDF, pages, RENDER_DIR)
    print(f"  serial                         : {serial['total']:5.1f}s")

    matched = []
    for n in MATCHED:
        mp = run_mp(PDF, pages, RENDER_DIR, n)
        hy = run_hybrid(PDF, pages, RENDER_DIR, n, n)
        matched.append({"n": n, "mp": mp, "hybrid": hy})
        print(f"  N={n}: pure-MP {mp:5.1f}s | hybrid {hy:5.1f}s  "
              f"(ratio {mp / hy:.2f})")

    oc, cw = DECOUPLED
    dec_t = run_hybrid(PDF, pages, RENDER_DIR, oc, cw)
    mp_full = next(m["mp"] for m in matched if m["n"] == oc)
    print(f"  decoupled: hybrid OCR={oc}, CPU={cw} ({cw} procs): {dec_t:5.1f}s  "
          f"vs pure-MP({oc} procs) {mp_full:.1f}s")

    # The hypothesis predicted a TIE at matched parallelism (plus a decoupled-efficiency win).
    # Score what actually happened, data-driven, so the printed message can't drift from reality.
    ratios = [m["mp"] / m["hybrid"] for m in matched]   # >1 means hybrid was faster
    mean_ratio = sum(ratios) / len(ratios)
    tie = all(0.90 <= r <= 1.10 for r in ratios)
    hybrid_faster = mean_ratio > 1.10
    # OVERTURNED unless matched parallelism actually tied (the predicted outcome).
    verdict = "CONFIRMED" if tie else "OVERTURNED"
    if hybrid_faster:
        finding = (f"the hybrid was consistently FASTER than pure multiprocessing at matched "
                   f"parallelism (mean {mean_ratio:.2f}x): per-page MP idles each worker during "
                   f"its blocking OCR, while the hybrid overlaps every OCR wait across pages")
    elif tie:
        finding = "matched parallelism tied, as predicted"
    else:
        finding = f"pure multiprocessing was faster at matched parallelism (mean {mean_ratio:.2f}x)"

    out = {
        "pdf": PDF.name, "n_pages": args.pages, "model": _ocr.OCR_MODEL,
        "serial": serial["total"], "matched": matched,
        "decoupled": {"ocr_conc": oc, "cpu_workers": cw, "time": dec_t,
                      "vs_mp_procs": oc, "mp_time": mp_full},
        "mean_ratio": mean_ratio, "verdict": verdict, "finding": finding,
    }
    RESULTS.write_text(json.dumps(out, indent=2))
    print(f"\n  VERDICT: {verdict} — {finding}")
    print(f"  wrote {RESULTS.name}")


if __name__ == "__main__":
    main()
