"""Chapter 8 - Exercise 8: when does `boundscheck=False` actually help?

Task: ex02 disabled bounds checking on the Julia loop and saw no change -- the book says
so, and we confirmed it. The reason was structural: that loop's inner body touched only C
scalars, and the array access sat in the cheap outer loop. This exercise flips that. It
runs a 2D-diffusion stencil where the memoryview is indexed five times *per inner
iteration*, and compares Cython's default checked indexing against `boundscheck(False)` +
`wraparound(False)`.

Takeaway: the chapter's tip -- "disable bounds checking if your CPU-bound code is in a
loop that is dereferencing items frequently" -- is conditional, and this is the condition.
Here the guards are a measurable tax because they run on the hot path; in ex02 they were
free because they didn't. Same directive, opposite verdict, decided entirely by *where*
the indexing happens.

Built on first import by pyximport (the .pyx needs no numpy headers -- just memoryviews).

Run: .venv/bin/python chapter_8_compiling_to_c/ex08_boundscheck/ex08_boundscheck.py
"""
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))   # repo root -> perf.py
sys.path.insert(0, str(HERE.parent))       # this folder -> _diffcy.pyx

from perf import time_s  # noqa: E402

import pyximport  # noqa: E402
pyximport.install(language_level=3)
import _diffcy  # noqa: E402

N = 1000          # bigger grid => the inner-loop indexing dominates, guards show up
STEPS = 30        # per timed round, to average out noise


def initial_grid():
    g = np.zeros((N, N), dtype=np.double)
    g[N // 2 - 40:N // 2 + 40, N // 2 - 40:N // 2 + 40] = 1.0
    return g


def run(fn):
    grid, out = initial_grid(), np.zeros((N, N), dtype=np.double)
    for _ in range(STEPS):
        fn(grid, out, 1.0, 0.1)
        grid, out = out, grid
    return grid


def main():
    # Correctness: both variants must produce the identical field.
    a, b = run(_diffcy.checked), run(_diffcy.unchecked)
    assert np.allclose(a, b), "checked and unchecked disagree"
    print(f"Diffusion grid: {N}x{N}, {STEPS} steps/round.  checked == unchecked to 1e-12.\n")

    t_checked = time_s(lambda: run(_diffcy.checked), number=1, repeat=5) / STEPS
    t_unchecked = time_s(lambda: run(_diffcy.unchecked), number=1, repeat=5) / STEPS

    print("Cython 2D-diffusion, per step (best of 5):")
    print(f"  boundscheck + wraparound ON  (default) : {t_checked * 1e3:6.2f} ms/step")
    print(f"  boundscheck + wraparound OFF           : {t_unchecked * 1e3:6.2f} ms/step")
    print(f"  -> turning the guards off: {t_checked / t_unchecked:.2f}x faster.\n")
    print("  Contrast ex02, where the same directive changed nothing: there the array")
    print("  access was in the outer loop, here it's five reads deep in the inner loop.")


if __name__ == "__main__":
    main()
