# Chapter 4 — Dictionaries and Sets: Practice Exercises

Runnable drills for *High Performance Python (3rd ed.)*, Chapter 4. Each exercise
lives in its own folder with an `exNN_name.py` benchmark (self-reports **time** via
`timeit` and **memory** via `tracemalloc` peak / `sys.getsizeof`, through the shared
`perf.py`), a `plot.py` that regenerates its `chart.png`, and a `README.md`.

Numbers are from **CPython 3.14.0 / macOS** — yours will differ.

```bash
.venv/bin/python chapter_4/ex01_hash_mask/ex01_hash_mask.py
```

**Core idea:** `O(1)` is a *promise conditional on a high-entropy hash*. The key is
hashed then masked into a bucket; collisions are resolved by a perturbed probe that
folds in high-order bits. A degenerate hash collapses the table back to an `O(n)`
linear scan.

See also [`hypothesis/`](hypothesis/) — investigative drills that go *beyond* the
book's stated benchmarks, each testing a falsifiable claim with a predicted outcome
and a verdict from real measurements.

## Exercises

| # | Exercise | What it shows |
| --- | --- | --- |
| [ex01](ex01_hash_mask/) | `hash_mask` | `hash(key) & (size-1)` by hand; why `Rome`/`Barcelona` collide in 8 buckets |
| [ex02](ex02_set_vs_list_unique/) | `set_vs_list_unique` | Uniqueness via a growing list vs a set; the speedup widens with N |
| [ex03](ex03_dict_vs_bisect/) | `dict_vs_bisect` | `dict` `O(1)` vs list+`bisect` `O(log n)`, with the memory price |
| [ex04](ex04_probing_trace/) | `probing_trace` | The perturbed probe sequence; collisions, lookup-miss, tombstone-on-delete |
| [ex05](ex05_point_hash/) | `point_hash` | Content-based `__hash__`/`__eq__` so a `set` deduplicates value-equal objects |
| [ex06](ex06_good_bad_hash/) | `good_bad_hash` | `BadHash` vs `GoodHash` vs a plain list — the cost of a bad hash |
| [ex07](ex07_twoletter_hash/) | `twoletter_hash` | Why a perfect hash is collision-free at one table size but not another |
| [ex08](ex08_resizing/) | `resizing` | Resize arithmetic, the shrink quirk, and amortized-insert timing |
| [ex09](ex09_int_hash/) | `int_hash` | The integer-hash identity and where finiteness creates collisions |

> `ex08` is a live demonstration of the chapter's own closing warning — *always
> re-profile performance assumptions across CPython versions.*

Companion notes: `Chapter 4 Dictionaries and Sets.md` in the Obsidian vault.
