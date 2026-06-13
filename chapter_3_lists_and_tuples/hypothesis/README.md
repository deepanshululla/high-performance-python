# Chapter 3 — Hypotheses

Investigative drills that go *beyond* the book's stated benchmarks — each tests a
falsifiable claim adjacent to the chapter, with a predicted outcome and a verdict
from real measurements (**CPython 3.14.0 / macOS**; yours will differ).

Each folder is self-contained: `benchmark.py` self-reports its numbers, `README.md`
states the hypothesis, results, and verdict.

| # | Hypothesis | Extends | Verdict |
| --- | --- | --- | --- |
| [H1](h01_tuple_freelist_cliff/) | The tuple freelist has a sharp time cliff at size 20→21 (but no memory cliff) | ex07 | ✅ Confirmed |
| [H2](h02_preallocation_vs_append/) | Preallocating a list beats append-growing it | ex05 | ✅ Confirmed (nuanced — memory win is cleaner than time) |
| [H3](h03_membership_position/) | `x in list` time is linear in the target's position | ex02 | ✅ Confirmed |

```bash
.venv/bin/python chapter_3/hypothesis/h01_tuple_freelist_cliff/benchmark.py
```
