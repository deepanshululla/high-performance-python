# Chapter 5 — Hypotheses

Investigative drills that go *beyond* the book's stated benchmarks — each tests a
falsifiable claim adjacent to the chapter, with a predicted outcome and a verdict
from real measurements (**CPython 3.14.0 / macOS**; yours will differ).

Each folder is self-contained: `benchmark.py` self-reports its numbers, `README.md`
states the hypothesis, results, and verdict.

| # | Hypothesis | Extends | Verdict |
| --- | --- | --- | --- |
| [H1](h01_yield_from_overhead/) | `yield from` is faster than manual `for x in sub: yield x` | ex06/ex08 | ✅ Confirmed (1.13× — smaller than predicted) |
| [H2](h02_generator_depth/) | Deep generator pipelines cost CPU linearly in depth (RAM stays flat) | ex06 | ✅ Confirmed (~11.5 ns/layer/item) |
| [H3](h03_iterator_impls/) | Native generators beat a hand-rolled `__next__` class | ex01 | ✅ Confirmed (class 2.8× slower) |

```bash
.venv/bin/python chapter_5/hypothesis/h01_yield_from_overhead/benchmark.py
```
