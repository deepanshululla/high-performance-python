# High Performance Python — Study Drills

Runnable, self-measuring practice exercises worked through *High Performance Python*, 3rd ed.
(Gorelick & Ozsvald, O'Reilly), one chapter at a time. The book explains *why* Python is slow
and how to make it fast; this repo turns each claim into a script you can run, with the timing
and memory numbers measured on this machine rather than quoted from the page.

The guiding principle across every chapter is **measured honesty**: each exercise isolates one
variable, asserts a correctness anchor so a faster-but-wrong version fails loudly, and ends in a
short writeup that drills from the surface number to the root cause. Where a result overturns the
book's framing on modern hardware (Apple Silicon, CPython 3.14, pandas 3.0's Copy-on-Write,
Cython 3.x), the surprise is reported, not smoothed over.

## Chapters

Each chapter is a self-contained folder with its own README index, a set of exercise
sub-folders, and (from Chapter 3 on) a `hypothesis/` directory of falsifiable drills that go
beyond the book. Every exercise folder holds a runnable benchmark script, a `chart.png`, and a
prose `README.md`.

| chapter | topic | drills |
| --- | --- | --- |
| [2 — Profiling to Find Bottlenecks](chapter_2_profiling_to_find_bottlenecks/) | the Julia-set workload profiled end to end: `cProfile`, `line_profiler`, `py-spy`, `scalene`, `memray`, `viztracer`, and flame graphs | profiling toolchain |
| [3 — Lists and Tuples](chapter_3_lists_and_tuples/) | dynamic-array overallocation, `bisect` search, the list-vs-tuple memory trade | 7 exercises, 4 hypotheses |
| [4 — Dictionaries and Sets](chapter_4_dictionaries_and_sets/) | hashing, open-addressing probes, load factor and resize, memory cost | 9 exercises, 6 hypotheses |
| [5 — Iterators and Generators](chapter_5_iterators_and_generators/) | lazy evaluation, the memory story of streaming vs materializing | 9 exercises, 4 hypotheses |
| [6 — Matrix and Vector Computation](chapter_6_matrix_and_vector_computation/) | numpy vectorization, in-place vs out-of-place, cache effects, `numexpr`, GPU/MPS | 12 exercises, 7 hypotheses |
| [7 — Pandas, Dask, Polars](chapter_7_pandas_dask_polars/) | row-iteration vehicles, the `concat` quadratic trap, Arrow storage, scaling engines | 9 exercises, 6 hypotheses |
| [8 — Compiling to C](chapter_8_compiling_to_c/) | Cython, Numba, Pythran, and the FFI ladder: ctypes, cffi, a CPython extension, f2py, Rust/PyO3 | 12 exercises |
| [9 — Asynchronous I/O](chapter_9_asynchronous_io/) | the event loop, coroutines and `TaskGroup`, an `aiohttp` crawler, concurrency sweeps, batched pipelining, and a real OCR pipeline | 9 exercises, 3 hypotheses |
| [10 — Multiprocessing](chapter_10_multiprocessing/) | Monte Carlo pi and prime checking across cores: process scaling, `chunksize`, IPC early-exit flags, zero-copy shared arrays, locking, fork vs spawn | 9 exercises, 1 hypothesis |
| [11 — Clusters and Job Queues](chapter_11_clusters_and_job_queues/) | IPython Parallel, Redis work queues and pub/sub vs consumer groups, delivery guarantees, message serialization, Docker overhead | 9 exercises, 1 hypothesis |
| [12 — Using Less RAM](chapter_12_using_less_ram/) | arrays vs numpy, sparse matrices, tries, feature hashing, and probabilistic structures (Morris, Bloom, HyperLogLog) | 10 exercises, 1 hypothesis |
| [13 — Lessons from the Field](chapter_13_lessons_from_the_field/) | practitioners' war stories made runnable: Aho-Corasick and spatial-index prefilters, the "wrong problem" proxy, defensive `pandera`, streaming, knowing your BLAS — changing the problem beats speeding up the work | 10 exercises, 1 hypothesis |

A repo-wide [`glossary.md`](glossary.md) collects the concepts, tools, and terms as the
exercises use them, following the book's arc.

## Setup

The repo is `uv`-managed. One sync installs every dependency the chapters use (numpy, pandas,
polars, dask, scikit-learn, numba, cython, cffi, pythran, torch, aiohttp, ipyparallel, redis,
msgpack, marisa-trie, mmh3, bitarray, and the profiling/visualization front-ends):

```bash
uv sync
```

A few chapters also reach for external tooling: Chapter 8 builds compiled extensions (clang,
optionally `gfortran` and `rustc`), and Chapters 10–11 use **Docker** to run a Redis container
(Chapter 11 starts and stops its own ephemeral one per exercise). Exercises that need a tool say
so in their README.

Benchmarked on **CPython 3.14 / Apple Silicon (10 cores)**, run from the repo root. Exercises
add the repo root to `sys.path` to import the two shared helpers:

- **`perf.py`** — `time_s(fn, number, repeat)`, `peak_bytes(fn)` (via `tracemalloc`), `human(n)`.
- **`vizutil.py`** — shared matplotlib styling (`setup`, `save`, `COLORS`) for the charts.

## Running a drill

Every exercise is a plain script that prints its own measurements:

```bash
# run any exercise (compiled chapters build their extensions on first run)
.venv/bin/python chapter_8_compiling_to_c/ex04_numba_jit/ex04_numba_jit.py

# most chapters have a visualizer that reuses each exercise's functions to (re)draw charts
.venv/bin/python chapter_8_compiling_to_c/visualize_exercises.py            # all + dashboard
.venv/bin/python chapter_8_compiling_to_c/visualize_exercises.py --only ex03  # just one
```

Start from a chapter's own README for the tour, the results table, and how to read each chart.

## Task runner (optional)

A [Taskfile](https://taskfile.dev) wraps the common workflows (install: `brew install go-task`).
The root `Taskfile.yml` includes a per-chapter Taskfile under a `chN:` namespace, and each
chapter Taskfile also runs standalone (`cd chapter_8_compiling_to_c && task`).

```bash
task                 # list the root tasks
task --list-all      # include every chapter task (ch2:… … ch12:…)
task setup           # uv sync
task docs            # start the documentation site (hot reload)

task ch8:viz         # regenerate Chapter 8 charts + dashboard
task ch3:smoke       # run every Chapter 3 exercise (asserts correctness)
task ch8:run -- ex04_numba_jit/ex04_numba_jit.py   # run one script
task run -- chapter_6_matrix_and_vector_computation/ex01_list_vs_numpy_norm/ex01_list_vs_numpy_norm.py

task smoke:all       # run every exercise in every chapter
task viz:all         # regenerate every chart (slow)
task clean           # remove compiled extensions + the docs build
```

## Documentation site

All of the chapter and exercise writeups are also published as a browsable, searchable
[Docusaurus](https://docusaurus.io/) site under [`website/`](website/). The chapter folders stay
the single source of truth — a sync step (`website/sync-docs.mjs`) generates the site's `docs/`
from them, co-locating each chart and rewriting inter-page links, so there's no duplicated
content to keep in step.

```bash
cd website
npm install        # first time only
npm start          # syncs from the repo, then serves with hot reload at http://localhost:3000
npm run build      # static production build into website/build/ (host anywhere)
npm run serve      # preview the production build
```

`npm run sync` (run automatically by `start`/`build`) rewrites `website/docs/` — don't edit it by
hand; edit the chapter READMEs or the authored guides in `website/content/`. The build is a
portable static bundle with offline search; publishing it (e.g. to GitHub Pages) later just means
setting `url`/`baseUrl` in `website/docusaurus.config.js` and adding a deploy step.

## Reference

Gorelick, M. & Ozsvald, I. *High Performance Python*, 3rd ed. (O'Reilly). Companion reading
notes (with "Key Insights" and "5 Whys" callouts) live in the author's Obsidian vault, one note
per chapter.
