---
name: hpp-chapter-exercises
description: Author runnable, measured practice exercises for a chapter of "High Performance Python (3rd ed.)" in the user's HPP study repo. Use when the user points at a chapter's Obsidian note (or names a chapter/topic) and asks to create practice exercises, drills, or benchmarks. Produces per-exercise folders (script + README + chart), a central visualizer, and a chapter index — every claim backed by a number measured on this machine.
---

# HPP Chapter Exercises

Build a chapter's worth of runnable, self-measuring practice drills in the user's
*High Performance Python* study repo, matching its established conventions exactly. The
defining value of this repo is **measured honesty**: every number in a README came from
running the code on this machine, and a surprising result is reported as the finding, not
smoothed over.

## When to use

The user points at `.../Books/HighPerformancePython3rdEdition/Chapter N <topic>.md` (or just
names the chapter/topic) and asks for practice exercises, drills, or benchmarks. Each chapter
is independent.

## Repo conventions (verify, don't assume — they drift)

Repo root: `/Users/deepanshu/PycharmProjects/random_practice/high_performance_python`.
Interpreter: `.venv/bin/python` from the repo root (run from root; scripts add root to
`sys.path`). Companion notes: `/Users/deepanshu/Dropbox/obsidian/.../HighPerformancePython3rdEdition/`.
The persistent memory `hpp-repo-structure` has the current layout — read it first, then
confirm against the newest existing chapter (conventions evolve; the latest chapter wins).

- **One folder per exercise**: `chapter_N_<slug>/exNN_<name>/` containing `exNN_<name>.py`,
  `README.md`, `chart.png`. Compiled chapters also hold sources (`.pyx`, `.c`, `setup.py`).
- **Hypotheses** (falsifiable drills beyond the book) optionally live in
  `chapter_N_<slug>/hypothesis/<hNN_name>/` — same shape, each with a predicted outcome and a
  VERDICT (CONFIRMED/OVERTURNED).
- **Shared helpers at repo root**: `perf.py` (`time_s(fn, number, repeat)`, `peak_bytes(fn)`,
  `human(nbytes)`) and `vizutil.py` (`plt, setup(), save(fig, __file__, subtitle=...), COLORS`).
  Import them via `sys.path.insert(0, repo_root)`; depth is `parents[2]` from an exercise folder.
- **Central `visualize_exercises.py`** at chapter root: imports each exercise module by path,
  **reuses its functions** to measure, writes `chart.png` per folder, tiles
  `exercises_dashboard.png`. Supports `--only exNN`. (Older chapters used per-folder `plot.py`;
  the central visualizer is the current pattern — check the newest chapter.)
- **Chapter `README.md`** is an index: intro prose, a Core-idea line, numbered
  **Verified learnings**, an exercise table, the dashboard image, a chapter-level "5 Whys", and
  an honest "what's reproduced / what isn't" note. Each exercise README has: intro prose,
  "What it measures" table, "What we found" prose, "Reading the chart", a "5 Whys" ending in a
  **Root cause** line, and a "Run" block.
- **Writing style**: flowing, explanatory prose, NOT dense bullets (memory `prefers-flowing-prose`).
  Match the newest chapter's voice.

## Process

1. **Read the chapter note fully** (it's long — page through it; don't answer from page 1). Pull
   out the running example, the book's tables/figures, and the concrete numbers to reproduce.
2. **Probe the toolchain BEFORE designing.** This is the lesson that saves the most rework: what
   actually builds on this machine decides which exercises can carry real numbers. Check
   compilers/runtimes the chapter needs (`cc`, `gfortran`, `rustc`, libomp, GPU), and
   `uv add` any missing Python deps. A technique that won't build gets *documented honestly* in
   the chapter README's "what isn't reproduced" note — never faked.
3. **Define a single shared workload** in a chapter-level helper (e.g. `_julia.py`) so every
   exercise times the *identical* computation on identical inputs and the numbers line up into
   the book's tables. Bake in a **correctness anchor** (a checksum the book gives, or one you
   verify once) and `assert` it in every exercise — a variant that gets fast by computing the
   wrong thing must fail loudly.
4. **Build one exercise at a time and RUN it.** Never write a batch of scripts and a batch of
   READMEs blind. Run the script, read the real numbers, *then* write the README around them.
   When a number contradicts the premise (it will), that's the best exercise — reframe honestly
   around the surprise (e.g. strength reduction is a *loss* in the interpreter). Verify cached
   rebuilds re-run cleanly.
5. **Generate charts** with the central visualizer reusing each exercise's functions; verify the
   dashboard PNG visually with the Read tool.
6. **Write READMEs** in flowing prose with the real measured numbers; note that absolute figures
   are machine-dependent while ratios are the lesson.
7. **Glossary**: add a chapter section to root `glossary.md` if the doc covers prior chapters.
8. **gitignore build artifacts**: add a chapter-local `.gitignore` for compiled outputs
   (`*.so`, `build/`, generated `.c`) but keep hand-written sources and charts tracked. Gitignore
   has **no inline comments** — put `#` comments on their own lines. Verify with `git check-ignore`.

## Compiled-extension gotchas (Chapter 8 and any FFI/Cython work)

- **pyximport** auto-compiles a `.pyx` on import — simplest for pure-Python Cython with no special
  flags. For numpy headers / OpenMP / custom flags, use an explicit `setup.py` +
  `cythonize`, built via subprocess on first run (mirrors the book), guarded by an `if .so exists`
  check so it builds once.
- **OpenMP on macOS**: Apple clang has no OpenMP runtime. Rather than force `brew install libomp`,
  auto-discover `omp.h` + `libomp.dylib` from (in order) an env var, this venv's **PyTorch**
  (it bundles both), then Homebrew paths. Compile with `-Xpreprocessor -fopenmp -I<inc>`, link
  `-L<lib> -lomp -Wl,-rpath,<lib> -Wl,-headerpad_max_install_names`. A bundled libomp often
  records a bogus absolute install-name, so post-build run
  `install_name_tool -change <bad> @rpath/libomp.dylib <so>` (the `@rpath/...` form is short
  enough to fit the load command). Fall back to a serial build if no runtime is found — Cython
  guards `prange` with `#ifdef _OPENMP`, so it still compiles and runs single-threaded.
- **Numba**: time the **cold** first call (compile) separately from **warm** (best of N); a
  `parallel=True` function compiles separately and has its own larger cold start.
- **ctypes vs cffi**: they call the same compiled symbol, so they're the same speed — the chart
  point is ergonomics/safety, not performance.
- **Pythran**: `#pythran export f(int, complex128[:], ...)` over a plain numpy function; build
  with the `pythran` CLI (find it next to `sys.executable`). Works on 3.14/Apple Silicon.
- **f2py (numpy 2.x)**: uses the **meson** backend, which shells out to `meson`/`ninja` — they
  live in the venv's bin, so set `PATH` to include `Path(sys.executable).parent` for the build
  subprocess or it dies with `FileNotFoundError: meson`. Needs `gfortran` (Homebrew `gcc`
  provides it). Pass numpy arrays with `order="F"` (Fortran is column-major).
- **Rust/PyO3**: pin `pyo3` to match the `numpy` crate's pyo3 (e.g. both **0.28**) or you get a
  `links = "python"` conflict. Three traps that each cost a debug cycle: (1) name the crate
  **directory** something other than the module name (e.g. `crate/`), or a same-named source dir
  shadows the installed module as an empty namespace package; (2) `maturin develop` installs into
  whatever **`VIRTUAL_ENV`** points at — set it explicitly to the project venv, since an inherited
  one may point at a sibling venv; (3) export the function under the Python name you call with
  `#[pyfunction(name = "evolve")]`, else it's exposed under the Rust fn name. Delete maturin's
  generated `.github/workflows/CI.yml` (a wheel-publish workflow you don't want triggering).
- **gitignore for compiled chapters**: ignore `*.so`, `build/`, `target/` (Rust, ~90MB!),
  Cython-generated `.c` (keep the `.pyx`), and `cython -a`'s `annot.html`/`annot.c`. Keep
  hand-written `.c`/`.h`/`.f90`/`.rs`/`.pyx`, `Cargo.toml`/`Cargo.lock`, and charts. gitignore has
  **no inline comments**. Verify with `git ls-files | grep -E '\.so$|/target/|...'`.

## Quality bar

- Every README number is reproducible by running the script. No invented figures.
- Each exercise isolates ONE variable so its win is attributable.
- Honest negatives are features: report the optimization that didn't help, the tool that won't
  build, the parallel speedup short of linear. The repo's credibility is the point.
- Match the newest chapter's structure and voice; when unsure, open it and copy the pattern.
- After finishing, update the `hpp-repo-structure` memory if the layout evolved.
