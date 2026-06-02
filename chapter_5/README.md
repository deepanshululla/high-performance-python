# Chapter 5 — Iterators and Generators: Practice Exercises

Runnable drills for *High Performance Python (3rd ed.)*, Chapter 5. Each script
self-reports **time** (`timeit`) and **memory** (`tracemalloc` peak, via the shared
`perf.py`) — so the memory wins are visible without an external profiler.

Numbers below are from **CPython 3.14.0 / macOS** — yours will differ.

```bash
.venv/bin/python chapter_5/ex01_for_deconstructed.py
# optional RSS-based view for the memory exercises:
.venv/bin/python -m memory_profiler chapter_5/ex02_fib_list_vs_gen.py
```

**Core idea:** a generator trades *stored data* for *recomputation*, keeping memory at
`O(1)` state no matter how many values flow through. Lazy evaluation is demand-driven,
so early termination is free — but the price is single-pass (online) access.

---

## `ex01_for_deconstructed.py`

`for` == `iter()` then `next()` until `StopIteration`; a generator *is* its own iterator.

- **Time** (loop over 1,000,000 items): prebuilt list **31.5 ms** vs generator **28.5 ms**.
- **Memory:** prebuilt list **peak 38.1 MB** vs generator **peak 728 B**.

**Learning:** a generator returns itself from `iter()` (no extra object); a list must
be built and stored first, then wrapped in a separate iterator — it pays to allocate
all N up front.

---

## `ex02_fib_list_vs_gen.py`

Fibonacci by list vs generator — the headline memory win.

- **Time** (100,000 numbers): list **170 ms** vs generator **126 ms** (~1.3× faster).
- **Memory:** list **445 MB** vs generator **27.6 KB** → **~16,500×** less memory
  (the list stores 100,000 *big* ints; the generator holds only `a, b`).

**Learning:** the structural win is memory — a generator never materializes the
sequence, so its footprint is `O(1)` state regardless of length.

---

## `ex03_len_trap.py`

`len([n for ...])` vs `sum(1 for ...)` — same answer, very different memory.

- **Time:** `len([...])` **623.8 ms** vs `sum(1 for ...)` **614.1 ms** (≈ equal).
- **Memory:** `len([...])` **111.3 MB** (materializes all matches) vs `sum(1 for ...)`
  **27.9 KB** (folds one value at a time).

**Learning:** the only code difference is `[]` vs `()`, but the list comprehension
re-materializes everything just to count and discard it.

---

## `ex04_infinite_fib.py`

Infinite `while True: yield` + three ways to count odd Fibonaccis below 5,000.

- **Time:** naive **0.66 µs**, transform **0.95 µs**, succinct (`takewhile`) **1.66 µs**.
- **Memory:** all `O(1)` — the infinite generator holds only `i, j`; `takewhile`/`break`
  terminate it, so "infinite" is never materialized.

**Learning:** generators express infinite series because the caller pulls only what
it needs; separating *generate* from *transform* makes the transform reusable.

---

## `ex05_itertools_drills.py`

`islice`/`chain`/`cycle`/`takewhile` over lazy streams.

- **Time** (sum first 1,000,000 ints): lazy `sum(islice(count(), N))` **10.4 ms** vs
  eager `sum(list(range(N)))` **19.6 ms**.
- **Memory:** lazy **peak 224 B** vs eager **peak 38.1 MB**.

**Learning:** `itertools` composition stays `O(1)` memory and is often faster too —
nothing is materialized between stages.

---

## `ex06_anomaly_pipeline.py`

Chained generators (read → group-by-day → filter → `islice`) over an *infinite* source.

- **Memory:** **flat ~26.4 MB** whether you pull 5, 10, or 20 anomalies (only ~one day
  of data is ever in flight).
- **Time:** grows with work pulled — **3.4 s / 6.6 s / 13.0 s** for first 5 / 10 / 20.

**Learning:** lazy evaluation makes memory depend on *window of state*, not dataset
size; `islice` stops the whole chain after the n-th result. (Retaining the full day
lists instead of just date ranges would make memory grow ~n×day — a deliberate choice.)

---

## `ex07_rolling_window.py`

Sliding window: tuple-rebuild vs deque+copy vs deque-in-place. **Counterintuitive result.**

- **Time** to slide across 50,000 items:

  | window | tuple-rebuild | deque + copy | deque in-place |
  | --- | --- | --- | --- |
  | 100 | 19.8 ms | 38.8 ms | **2.3 ms** |
  | 1,000 | 121 ms | 283 ms | **2.5 ms** |
  | 5,000 | 842 ms | 1,174 ms | **2.5 ms** |

- **Memory:** all variants hold exactly one window of state.

**Learning:** a deque gives `O(1)` append/popleft, but **copying to a tuple on every
yield is `O(window)` and erases the advantage** — `deque+copy` is no faster than
tuple-rebuild. The deque only pays off (flat ~2.5 ms regardless of window) when the
consumer reads the *live* window in place and never retains it. This is exactly the
book's caveat, measured.

---

## `ex08_eager_to_lazy.py`

Convert a load-everything function into a streaming pipeline; find the first match in a 1,000,001-line file.

- **Time:** eager (load all) **139 ms** vs lazy (stop early) **~0.0 ms**.
- **Memory:** eager **peak 140.3 MB** vs lazy **peak 147.4 KB**.

**Learning:** the lazy pipeline reads ~one line and allocates almost nothing because
the match is near the top; the eager version reads and stores all 1M lines first.
Trade-off: the lazy result is single-pass.

---

## `ex09_lazy_builtins.py`

Which built-ins are lazy vs eager.

- **Classification:** lazy — `map`/`zip`/`filter`/`reversed`/`enumerate`/`range`/`dict.items`;
  eager — `sorted`/`list`.
- **Memory** (sum `2*x` over 1,000,000): `sum(map(...))` **peak 464 B** vs
  `sum(list(map(...)))` **peak 38.6 MB**.

**Learning:** wrapping a lazy iterator in `list()` throws away the streaming win;
a 100k `zip` holds only the current pair.

---

Companion notes: `Chapter 5 Iterators And Generators.md` in the Obsidian vault.
