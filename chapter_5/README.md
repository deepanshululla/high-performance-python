# Chapter 5 — Iterators and Generators: Practice Exercises

Runnable drills for *High Performance Python (3rd ed.)*, Chapter 5. Each exercise
lives in its own folder with a self-contained benchmark (`<exNN_name>.py`), a chart
generator (`plot.py`), a rendered `chart.png`, and a `README.md`. Every benchmark
self-reports **time** (`timeit`) and **memory** (`tracemalloc` peak, via the shared
`perf.py`) — so the memory wins are visible without an external profiler.

Numbers in each exercise are from **CPython 3.14.0 / macOS** — yours will differ.

```bash
.venv/bin/python chapter_5/ex01_for_deconstructed/ex01_for_deconstructed.py
# optional RSS-based view for the memory exercises:
.venv/bin/python -m memory_profiler chapter_5/ex02_fib_list_vs_gen/ex02_fib_list_vs_gen.py
```

**Core idea:** a generator trades *stored data* for *recomputation*, keeping memory at
`O(1)` state no matter how many values flow through. Lazy evaluation is demand-driven,
so early termination is free — but the price is single-pass (online) access.

See also [`hypothesis/`](hypothesis/) — investigative drills that go *beyond* the
book's benchmarks, each testing a falsifiable claim adjacent to the chapter.

## Exercises

| # | Exercise | What it shows |
| --- | --- | --- |
| [ex01](ex01_for_deconstructed/) | `for` deconstructed | `for` == `iter()` then `next()` until `StopIteration`; a generator *is* its own iterator |
| [ex02](ex02_fib_list_vs_gen/) | Fibonacci: list vs generator | The headline memory win — generator never materializes the sequence (~16,500× less RAM) |
| [ex03](ex03_len_trap/) | the `len([...])` trap | `len([...])` vs `sum(1 for ...)`: same answer, huge memory gap — only `[]` vs `()` |
| [ex04](ex04_infinite_fib/) | infinite Fibonacci | Infinite `while True: yield` + early termination three ways; all `O(1)` memory |
| [ex05](ex05_itertools_drills/) | itertools drills | `islice`/`chain`/`cycle`/`takewhile` stay `O(1)` memory and are often faster |
| [ex06](ex06_anomaly_pipeline/) | lazy anomaly pipeline | Chained generators over an infinite source: memory flat, time grows with work pulled |
| [ex07](ex07_rolling_window/) | rolling window: tuple vs deque | Counterintuitive — copying the deque to a tuple each yield erases its advantage |
| [ex08](ex08_eager_to_lazy/) | eager to lazy | Streaming pipeline + early termination: first match in a 1M-line file, ~one line read |
| [ex09](ex09_lazy_builtins/) | lazy vs eager built-ins | Which built-ins stream (`map`/`zip`/`filter`/…) vs materialize (`sorted`/`list`) |

Companion notes: `Chapter 5 Iterators And Generators.md` in the Obsidian vault.
