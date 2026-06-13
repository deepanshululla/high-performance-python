---
title: Getting started
sidebar_label: Getting started
sidebar_position: 1
slug: /getting-started
---

# Getting started

The drills are Python scripts you run from the repository root. They print their own timing and
memory numbers, so there's nothing to read off a separate profiler for the basics.

## Prerequisites

- **[uv](https://docs.astral.sh/uv/)** — the package/environment manager the repo is built
  around.
- **Python 3.14** — uv will fetch it if you don't have it.
- A **C compiler** (clang/gcc) — only for Chapter 8's Cython/FFI drills. macOS ships clang with
  the Xcode command-line tools.

Chapter 8 has a few *optional* extras, each needed only for the drill that uses it. The chapter
degrades gracefully when one is missing:

- **OpenMP runtime** for the parallel Cython drills — sourced automatically from the venv's
  PyTorch on macOS, so usually nothing to install.
- **gfortran** (via Homebrew `gcc`) for the f2py/Fortran drill.
- **Rust** (`rustc`/`cargo`) plus `maturin` for the PyO3 drill.

## Install

```bash
uv sync
```

That creates `.venv/` and installs every dependency the chapters use — numpy, pandas, polars,
dask, scikit-learn, numba, cython, cffi, pythran, torch, plus the profiling and visualization
front-ends.

## Run a drill

Run any exercise script directly. Compiled chapters (Chapter 8) build their extension on the
first run and cache it afterward:

```bash
.venv/bin/python chapter_8_compiling_to_c/ex04_numba_jit/ex04_numba_jit.py
```

Each script prints a results table and asserts its correctness anchor — if the assertion holds,
the numbers are trustworthy.

## Regenerate the charts

Most chapters ship a visualizer that re-imports each exercise's own functions, re-measures, and
redraws every `chart.png` plus a combined dashboard:

```bash
# every chart in a chapter, plus its dashboard
.venv/bin/python chapter_8_compiling_to_c/visualize_exercises.py
# just one exercise
.venv/bin/python chapter_8_compiling_to_c/visualize_exercises.py --only ex03
```

## Run this documentation site

The site lives in `website/` and is generated from the chapter folders. From `website/`:

```bash
npm install          # first time only
npm start            # syncs docs/ from the repo, then serves with hot reload at :3000
npm run build        # static production build into website/build/
npm run serve        # preview the production build locally
```

`npm run sync` (run automatically by `start` and `build`) regenerates `website/docs/` from the
repo's `chapter_*/` folders and `glossary.md`. **Don't edit `website/docs/` by hand** — it's
overwritten on every sync. Edit the chapter READMEs (the source of truth) or the authored guides
in `website/content/` instead.
