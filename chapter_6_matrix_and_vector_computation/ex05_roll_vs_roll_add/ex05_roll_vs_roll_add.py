"""Chapter 6 - Exercise 5: specialize np.roll into a custom roll_add (Example 6-16).

Task: np.roll allocates a new array on every call and carries general-purpose
machinery for arbitrary shifts/axes. We only ever shift by +/-1 on axis 0 or 1
and immediately add the result into an accumulator. Write a `roll_add` that does
exactly that with fancy indexing -- no temporary, no generality -- prove it
matches np.roll, then time the two laplacians.

Takeaway: removing generality you don't need *can* remove instructions, branches,
and allocations. The book measured a ~7% win from this. But this is also a
cautionary tale (see the scipy story in the chapter): on a modern, heavily
optimized numpy, np.roll may already be fast enough that the hand-rolled version
ties or even loses -- so ALWAYS benchmark, never assume. The cost of specializing
is readability -- hence the docstring + test, as the book stresses.

Run: .venv/bin/python chapter_6/ex05_roll_vs_roll_add.py
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from perf import time_s  # noqa: E402

GRID = 512
ITERS = 300


def roll_add(rollee, shift, axis, out):
    """out += np.roll(rollee, shift, axis=axis), assuming rollee is 2D, shift is
    +/-1, and axis is 0 or 1. Done in-place with fancy indexing -- no temporary."""
    if shift == 1 and axis == 0:
        out[1:, :] += rollee[:-1, :]
        out[0, :] += rollee[-1, :]
    elif shift == -1 and axis == 0:
        out[:-1, :] += rollee[1:, :]
        out[-1, :] += rollee[0, :]
    elif shift == 1 and axis == 1:
        out[:, 1:] += rollee[:, :-1]
        out[:, 0] += rollee[:, -1]
    elif shift == -1 and axis == 1:
        out[:, :-1] += rollee[:, 1:]
        out[:, -1] += rollee[:, 0]


def test_roll_add():
    rollee = np.asarray([[1, 2], [3, 4]])
    for shift in (-1, +1):
        for axis in (0, 1):
            out = np.asarray([[6, 3], [9, 2]])
            expected = np.roll(rollee, shift, axis=axis) + out
            roll_add(rollee, shift, axis, out)
            assert np.all(expected == out), (shift, axis)


def laplacian_roll(grid, out):
    np.copyto(out, grid)
    out *= -4
    out += np.roll(grid, +1, 0)
    out += np.roll(grid, -1, 0)
    out += np.roll(grid, +1, 1)
    out += np.roll(grid, -1, 1)


def laplacian_roll_add(grid, out):
    np.copyto(out, grid)
    out *= -4
    roll_add(grid, +1, 0, out)
    roll_add(grid, -1, 0, out)
    roll_add(grid, +1, 1, out)
    roll_add(grid, -1, 1, out)


def run(laplacian, num_iterations, n):
    grid = np.zeros((n, n))
    scratch = np.zeros((n, n))
    lo, hi = int(n * 0.4), int(n * 0.5)
    grid[lo:hi, lo:hi] = 0.005
    for _ in range(num_iterations):
        laplacian(grid, scratch)
        scratch *= 0.1
        scratch += grid
        grid, scratch = scratch, grid
    return grid


def main():
    test_roll_add()
    print("test_roll_add passed: roll_add matches np.roll for all +/-1 shift/axis combos.")

    a = run(laplacian_roll, ITERS, GRID)
    b = run(laplacian_roll_add, ITERS, GRID)
    assert np.allclose(a, b), "the two laplacians diverged!"
    print(f"Both laplacians agree after {ITERS} iterations "
          f"(max abs diff {np.max(np.abs(a - b)):.2e})")

    t_roll = time_s(lambda: run(laplacian_roll, ITERS, GRID), number=1, repeat=3)
    t_add = time_s(lambda: run(laplacian_roll_add, ITERS, GRID), number=1, repeat=3)
    print(f"\n{GRID}x{GRID} grid, {ITERS} iterations:")
    print(f"  np.roll laplacian:   {t_roll * 1e3:8.1f} ms  (allocates 4 temporaries/iter)")
    print(f"  custom roll_add:     {t_add * 1e3:8.1f} ms  (in-place, no temporaries)")
    if t_add < t_roll:
        print(f"  -> custom is ~{t_roll / t_add:.2f}x faster: same math, fewer allocations + branches.")
    else:
        print(f"  -> custom is ~{t_add / t_roll:.2f}x SLOWER here -- the specialization did NOT pay off.")
        print("     Modern np.roll is already well optimized; the hand-rolled version's extra")
        print("     Python-level statements cost more than the temporaries it avoids.")
    print("     Lesson (the chapter's cautionary tale): hypothesize, then BENCHMARK. Never")
    print("     assume specialized code is faster -- and weigh any win against lost readability.")


if __name__ == "__main__":
    main()
