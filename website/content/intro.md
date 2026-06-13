---
title: High Performance Python — Study Drills
sidebar_label: Intro
sidebar_position: 0
slug: /
---

# High Performance Python — Study Drills

A worked, runnable companion to *High Performance Python*, 3rd ed. (Gorelick & Ozsvald,
O'Reilly). The book explains **why** Python is slow and how to make it fast; this project turns
each claim into a script you can run, with the timing and memory numbers **measured on real
hardware** rather than quoted from the page.

Every chapter of the book becomes a folder of small, focused exercises. Every exercise is a
self-contained benchmark that prints its own measurements, draws a chart, and ends in a short
writeup. This site is a browsable, searchable view of all of them.

## The one principle: measured honesty

Each drill is built to the same standard:

- **One variable at a time.** An exercise changes a single thing — a data structure, a
  compiler flag, a storage backend — so any speedup is attributable to that change and nothing
  else.
- **A correctness anchor.** Every script asserts a known-good result (a fixture checksum, or
  agreement with a reference implementation) so a version that gets *fast* by quietly computing
  the *wrong* thing fails loudly instead of lying in a chart.
- **Real numbers, including the inconvenient ones.** Results are measured on this machine
  (Apple Silicon, CPython 3.14). Where a result *overturns* the book's framing on modern
  hardware — a "strength reduction" that's actually slower in the interpreter, a pandas gap that
  Copy-on-Write already closed — the surprise is reported, not smoothed over.

## How to read a drill

Each exercise page follows the same shape, so you can skim or go deep:

1. **What it measures** — the task and a results table.
2. **What we found** — the prose explanation, including the honest negatives.
3. **Reading the chart** — how to interpret the figure.
4. **5 Whys** — a root-cause drill from the surface number down to the mechanism.
5. **Run** — the exact command to reproduce it.

New here? Start with **[Getting started](/getting-started)** to set up and run your first drill,
then **[Conventions](/conventions)** for how the drills are built and the shared helpers they use.

## Chapters

| chapter | topic |
| --- | --- |
| [2 — Profiling to Find Bottlenecks](/chapter-2) | the Julia-set workload profiled end to end: `cProfile`, `line_profiler`, `py-spy`, `scalene`, `memray`, `viztracer`, flame graphs |
| [3 — Lists and Tuples](/chapter-3) | dynamic-array overallocation, `bisect`, the list-vs-tuple memory trade |
| [4 — Dictionaries and Sets](/chapter-4) | hashing, open-addressing probes, load factor and resize, memory cost |
| [5 — Iterators and Generators](/chapter-5) | lazy evaluation, the memory story of streaming vs materializing |
| [6 — Matrix and Vector Computation](/chapter-6) | numpy vectorization, in-place vs out-of-place, cache effects, `numexpr`, GPU/MPS |
| [7 — Pandas, Dask, Polars](/chapter-7) | row-iteration vehicles, the `concat` quadratic trap, Arrow storage, scaling engines |
| [8 — Compiling to C](/chapter-8) | Cython, Numba, Pythran, and the FFI ladder: ctypes, cffi, a CPython extension, f2py, Rust/PyO3 |

Cross-cutting terms are collected in the **[Glossary](/glossary)**.
