---
title: Conventions
sidebar_label: Conventions
sidebar_position: 2
slug: /conventions
---

# Conventions

How the drills are organized and built — useful if you want to read the source, add an
exercise, or understand why the numbers are trustworthy.

## Anatomy of an exercise

Each chapter is a folder (`chapter_N_<slug>/`). Inside, every exercise gets its own
sub-folder holding three things:

```
chapter_8_compiling_to_c/
├── README.md                      # chapter index: intro, results, exercise table, dashboard
├── _julia.py                      # shared workload (per chapter, where relevant)
├── visualize_exercises.py         # redraws every chart + the dashboard
├── exercises_dashboard.png
└── ex01_julia_baseline/
    ├── ex01_julia_baseline.py     # the runnable benchmark
    ├── chart.png                  # its figure
    └── README.md                  # writeup: measures / found / chart / 5 Whys / run
```

From Chapter 3 on, chapters also have a `hypothesis/` directory of **falsifiable drills** that go
beyond the book — each states a prediction and ends in a verdict (CONFIRMED / OVERTURNED),
benchmarked and charted the same way.

## Shared helpers

Two small modules at the repo root keep the drills consistent. Exercises add the repo root to
`sys.path` and import them.

### `perf.py` — timing and memory

| function | what it does |
| --- | --- |
| `time_s(fn, number=1, repeat=5)` | best per-call wall time in seconds (`min` of `repeat` rounds via `timeit`) |
| `peak_bytes(fn)` | peak Python-heap bytes allocated during one call, via `tracemalloc` |
| `human(nbytes)` | format a byte count as `B`/`KB`/`MB`/`GB` |

`tracemalloc` numbers are smaller than RSS (they exclude interpreter overhead) but are
reproducible and isolate the allocation the exercise cares about.

### `vizutil.py` — chart styling

| symbol | what it does |
| --- | --- |
| `setup()` | apply the shared matplotlib rcParams (fonts, grid, colors) |
| `save(fig, __file__, subtitle=..., name="chart.png")` | tidy, caption, and write the PNG next to the calling file |
| `COLORS` | the shared palette dict |

## Patterns that make the numbers trustworthy

- **A shared workload per chapter.** Where a chapter optimizes one thing many ways (e.g.
  Chapter 8's Julia loop in `_julia.py`), every exercise times the *identical* computation on
  *identical* inputs, so the results line up directly into the book's comparison tables.
- **A correctness anchor in every script.** A fixture checksum (the Julia grid always sums to
  `33,219,980`) or agreement-to-tolerance with a reference. A faster-but-wrong variant fails the
  assertion rather than producing a misleading chart.
- **Probe the toolchain, report honestly.** Especially in Chapter 8: what actually builds on the
  machine decides which drills carry real numbers; anything that won't build is documented as
  such, never faked.
- **Ratios over absolutes.** Absolute timings are machine-specific (this machine runs the book's
  pure-Python baseline about twice as fast as the authors' laptop). The *ratios* between
  approaches are the portable lesson, and the writeups lead with them.

## This docs site

The site under `website/` does not duplicate any content. `website/sync-docs.mjs` generates
`website/docs/` from the chapter READMEs, the hypothesis writeups, and `glossary.md` on every
build, co-locating each chart and rewriting inter-page links. The chapter folders remain the
single source of truth; the authored guides you're reading now live in `website/content/`. See
**[Getting started](/getting-started)** for the commands.
