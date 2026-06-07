# Chapter 3 — Lists and Tuples: Practice Exercises

Runnable drills for *High Performance Python (3rd ed.)*, Chapter 3. Each exercise
lives in its own folder: read the script's docstring for the task, try it
yourself, then run the reference implementation. Every script self-reports
**time** (`timeit`) and **memory** (`tracemalloc` peak, via the shared `perf.py`
helper), and ships a `plot.py` that regenerates its `chart.png`.

All numbers below are from **CPython 3.14.0 / macOS** — yours will differ, and
that variance is itself part of the lesson. tracemalloc peaks measure Python-heap
allocations (smaller than RSS) but isolate the allocation each exercise cares about.

```bash
.venv/bin/python chapter_3/ex02_binary_search/ex02_binary_search.py
```

**Core idea:** position *is* address. Contiguous, uniform-stride memory gives `O(1)`
indexing and `O(log n)` search on sorted data — at the cost of an eventual `O(n)`
resize-and-copy that lists amortize via overallocation. Tuples drop the headroom
and bookkeeping in exchange for immutability.

See also [`hypothesis/`](hypothesis/) — investigative drills that go *beyond* the
book's benchmarks, each testing a falsifiable claim with a predicted outcome and a
verdict from real measurements.

## Exercises

| Exercise | What it shows |
| --- | --- |
| [ex02_binary_search](ex02_binary_search/) | `O(log n)` binary search vs the `O(n)` linear scan `list.index` performs |
| [ex03_bisect_vs_dict](ex03_bisect_vs_dict/) | One `bisect` lookup vs building a `set` — time *and* the memory price of `O(1)` |
| [ex04_find_closest](ex04_find_closest/) | Nearest-value lookup with `bisect`, keeping the list sorted via `insort` |
| [ex05_overallocation](ex05_overallocation/) | Reverse-engineering CPython's list growth formula and append vs `list()` cost |
| [ex06_memory_comp_list_tuple](ex06_memory_comp_list_tuple/) | The "48 MB" experiment: comprehension vs `list([...])` vs `tuple([...])` memory |
| [ex07_instantiation_timing](ex07_instantiation_timing/) | How fast and how large a list literal is vs a tuple, across the freelist boundary |
| [ex09_custom_ordering](ex09_custom_ordering/) | Making a custom object sortable + binary-searchable with `total_ordering` |

---

Companion notes: `Chapter 3 Lists And tuples.md` in the Obsidian vault.
