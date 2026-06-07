"""Chapter 6 - Exercise 4: cut numpy allocations with a scratch buffer (Examples 6-9, 6-13).

Task: take the naive numpy diffusion (allocates new arrays every `evolve`) and
rewrite it to preallocate one scratch grid, do all math in-place, then swap
references. Compare per-iteration time and peak memory.

Takeaway: the naive `grid = grid + dt*D*laplacian(grid)` allocates several
temporaries per iteration; each first-touch triggers a minor page fault (a
kernel round-trip that also flushes cache and breaks pipelining). Preallocating
`scratch` once and using `+=`/`copyto` keeps execution on the fast in-process
path -- the swap is just a cheap reference rename, not a data copy.

Run: .venv/bin/python chapter_6/ex04_numpy_diffusion_memory.py
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from perf import peak_bytes, time_s, human  # noqa: E402

GRID = 512
ITERS = 200


# --- naive: allocates temporaries every iteration (Example 6-9) ---------------
def laplacian_naive(grid):
    return (np.roll(grid, +1, 0) + np.roll(grid, -1, 0)
            + np.roll(grid, +1, 1) + np.roll(grid, -1, 1) - 4 * grid)


def run_naive(num_iterations, n):
    grid = np.zeros((n, n))
    lo, hi = int(n * 0.4), int(n * 0.5)
    grid[lo:hi, lo:hi] = 0.005
    for _ in range(num_iterations):
        grid = grid + 0.1 * laplacian_naive(grid)   # new array each call
    return grid


# --- in-place: one scratch buffer, swap references (Example 6-13) -------------
def laplacian_inplace(grid, out):
    np.copyto(out, grid)
    out *= -4
    out += np.roll(grid, +1, 0)
    out += np.roll(grid, -1, 0)
    out += np.roll(grid, +1, 1)
    out += np.roll(grid, -1, 1)


def evolve_inplace(grid, dt, out, D=1):
    laplacian_inplace(grid, out)
    out *= D * dt
    out += grid


def run_inplace(num_iterations, n):
    grid = np.zeros((n, n))
    scratch = np.zeros((n, n))
    lo, hi = int(n * 0.4), int(n * 0.5)
    grid[lo:hi, lo:hi] = 0.005
    for _ in range(num_iterations):
        evolve_inplace(grid, 0.1, scratch)
        grid, scratch = scratch, grid           # cheap: just renames references
    return grid


def main():
    naive = run_naive(ITERS, GRID)
    inplace = run_inplace(ITERS, GRID)
    assert np.allclose(naive, inplace), "naive and in-place diverged!"
    print(f"Naive and in-place agree after {ITERS} iterations "
          f"(max abs diff {np.max(np.abs(naive - inplace)):.2e})")

    t_naive = time_s(lambda: run_naive(ITERS, GRID), number=1, repeat=3)
    t_inplace = time_s(lambda: run_inplace(ITERS, GRID), number=1, repeat=3)
    print(f"\n{GRID}x{GRID} grid, {ITERS} iterations:")
    print(f"  naive (alloc/iter): {t_naive * 1e3:8.1f} ms   peak {human(peak_bytes(lambda: run_naive(ITERS, GRID)))}")
    print(f"  in-place (scratch): {t_inplace * 1e3:8.1f} ms   peak {human(peak_bytes(lambda: run_inplace(ITERS, GRID)))}")
    print(f"  -> in-place is ~{t_naive / t_inplace:.2f}x faster and holds less peak memory:")
    print("     no per-iteration temporaries, so fewer minor page faults and no pipeline stalls.")
    print("     (np.roll still allocates 4 temporaries -- ex05 removes those too.)")


if __name__ == "__main__":
    main()
