# Chapter 9 — Hypothesis Lab

Two falsifiable drills that push the chapter's CPU+I/O lesson past the book, both built on the
real OCR pipeline of [ex09](../ex09_ocr_pipeline/): render a PDF page (CPU), transcribe it with a
live `claude -p --model haiku` call (I/O), and run a heavy pure-Python keyword analysis (CPU).
Because the OCR stage is a real LLM call, every number here is **single-run and
nondeterministic** — captured once into each folder's `results.json`, with the chart redrawn from
that capture. The claim in each case is the *shape and ordering* of the result, not the seconds.

The two together tell one story: **async hides I/O behind I/O, but a heavy GIL-bound CPU stage
becomes a floor that only multiple processes can lower.** h01 finds that floor; h02 breaks
through it.

| # | hypothesis | verdict | the finding |
| --- | --- | --- | --- |
| h01 | [optimal OCR concurrency](h01_ocr_concurrency/) | **CONFIRMED** | speedup saturates at a knee (~c=4) and plateaus on the serial-CPU floor — more concurrency can't lower a CPU-bound floor |
| h02 | [GIL / process pool](h02_gil_process_pool/) | **CONFIRMED** | offloading the CPU stages to a process pool beats async-only by 1.28× (3.0× over serial) — asyncio + multiprocessing compose |

![hypothesis dashboard](hypothesis_dashboard.png)

## Why these two

The base chapter (ex01–ex08) and even ex09 show asyncio reclaiming I/O wait. But ex09 also showed
the speedup capping at ~2× once a real CPU stage entered the pipeline. These hypotheses isolate
*why* and *what to do about it*:

- **h01** proves the cap is real and locates it: raising OCR concurrency stops helping at the
  point where the overlapped I/O drops below the serialized CPU sum. The bottleneck has moved from
  the network to a single CPU core under the GIL.
- **h02** proves the way past it: a `ProcessPoolExecutor` runs the GIL-bound render/analyze in
  parallel across cores while the event loop keeps juggling the OCR I/O. This is the concrete
  bridge to Chapter 10 — asyncio for the I/O, processes for the CPU, used together.

## Reproduce

```bash
# real captures (each spends tokens; writes results.json)
.venv/bin/python chapter_9_asynchronous_io/hypothesis/h01_ocr_concurrency/benchmark.py --pages 6
.venv/bin/python chapter_9_asynchronous_io/hypothesis/h02_gil_process_pool/benchmark.py --pages 6

# redraw charts from the captures (free) + refresh the dashboard
.venv/bin/python chapter_9_asynchronous_io/hypothesis/h01_ocr_concurrency/benchmark.py --plot
.venv/bin/python chapter_9_asynchronous_io/hypothesis/h02_gil_process_pool/benchmark.py --plot
.venv/bin/python chapter_9_asynchronous_io/hypothesis/visualize.py
```
