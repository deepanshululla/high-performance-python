# Chapter 4 — Hypotheses

Investigative drills that go *beyond* the book's stated benchmarks — each tests a
falsifiable claim adjacent to the chapter, with a predicted outcome and a verdict
from real measurements (**CPython 3.14.0 / macOS**; yours will differ).

Each folder is self-contained: `benchmark.py` self-reports its numbers, `README.md`
states the hypothesis, results, and verdict.

| # | Hypothesis | Extends | Verdict |
| --- | --- | --- | --- |
| [H1](h01_insert_sawtooth/) | Dict inserts hide an O(n) resize "sawtooth" behind the amortized average | ex08 | ✅ Confirmed (19 spikes; last = 110,094× a normal insert) |
| [H2](h02_collision_entropy_curve/) | Lookup time degrades smoothly as hash entropy drops | ex06 | ✅ Confirmed (curve, with a buckets-vs-keys threshold) |
| [H3](h03_eafp_vs_lbyl/) | The best dict-access idiom depends on the hit rate | new | ✅ Confirmed (clean 3-way crossover) |
| [H4](h04_str_hash_caching/) | String hashing is O(len), but CPython caches it | new | ✅ Confirmed (up to 413×) |
| [H5](h05_slots_memory/) | `__slots__` shrinks the ex05 Point without changing its behavior | ex05 | ✅ Confirmed (1.45× less, ~40 B/instance) |

```bash
.venv/bin/python chapter_4/hypothesis/h01_insert_sawtooth/benchmark.py
```
