"""Chapter 6 - Exercise 2: 2D diffusion, pure Python vs numpy (Examples 6-3, 6-6, 6-9).

Task: solve the 2D diffusion equation three ways: (a) pure Python that allocates a
fresh `out` grid every call, (b) pure Python that preallocates one scratch grid and
swaps references (Example 6-6), and (c) numpy + `roll`. Verify all agree, then
compare time and peak memory.

Takeaway: the pure-Python grid is a list of lists of *pointers* -- the actual
floats are scattered across RAM, so every cell access is two pointer lookups and
nothing vectorizes (the von Neumann bottleneck made concrete). Preallocating the
output buffer (b) shaves a little off the Python version by avoiding a grid
allocation per iteration -- but it cannot fix the fragmentation, so numpy's
contiguous typed block + vectorized C still wins by a wide margin on the exact
same algorithm.

Run: .venv/bin/python chapter_6/ex02_diffusion_python_vs_numpy.py
"""
import pathlib
import sys

import numpy as np
from numpy import roll, zeros

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from perf import peak_bytes, time_s, human  # noqa: E402

GRID = 128          # pure Python is O(N^2) per iter -- keep it modest
ITERS = 50


# --- pure Python (Example 6-3) ------------------------------------------------
def evolve_py(grid, dt, shape, D=1.0):
    xmax, ymax = shape
    out = [[0.0] * ymax for _ in range(xmax)]
    for i in range(xmax):
        for j in range(ymax):
            grid_xx = grid[(i + 1) % xmax][j] + grid[(i - 1) % xmax][j] - 2.0 * grid[i][j]
            grid_yy = grid[i][(j + 1) % ymax] + grid[i][(j - 1) % ymax] - 2.0 * grid[i][j]
            out[i][j] = grid[i][j] + D * (grid_xx + grid_yy) * dt
    return out


def run_py(num_iterations, n):
    grid = [[0.0] * n for _ in range(n)]
    lo, hi = int(n * 0.4), int(n * 0.5)
    for i in range(lo, hi):
        for j in range(lo, hi):
            grid[i][j] = 0.005
    for _ in range(num_iterations):
        grid = evolve_py(grid, 0.1, (n, n))
    return grid


# --- pure Python, allocations reduced (Example 6-6) ---------------------------
def evolve_py_inplace(grid, dt, out, shape, D=1.0):
    xmax, ymax = shape
    for i in range(xmax):
        for j in range(ymax):
            grid_xx = grid[(i + 1) % xmax][j] + grid[(i - 1) % xmax][j] - 2.0 * grid[i][j]
            grid_yy = grid[i][(j + 1) % ymax] + grid[i][(j - 1) % ymax] - 2.0 * grid[i][j]
            out[i][j] = grid[i][j] + D * (grid_xx + grid_yy) * dt


def run_py_prealloc(num_iterations, n):
    grid = [[0.0] * n for _ in range(n)]
    nxt = [[0.0] * n for _ in range(n)]          # allocated ONCE, reused every iter
    lo, hi = int(n * 0.4), int(n * 0.5)
    for i in range(lo, hi):
        for j in range(lo, hi):
            grid[i][j] = 0.005
    for _ in range(num_iterations):
        evolve_py_inplace(grid, 0.1, nxt, (n, n))
        grid, nxt = nxt, grid                    # cheap reference swap
    return grid


# --- numpy (Example 6-9) ------------------------------------------------------
def laplacian_np(grid):
    return (roll(grid, +1, 0) + roll(grid, -1, 0)
            + roll(grid, +1, 1) + roll(grid, -1, 1) - 4 * grid)


def evolve_np(grid, dt, D=1.0):
    return grid + dt * D * laplacian_np(grid)


def run_np(num_iterations, n):
    grid = zeros((n, n))
    lo, hi = int(n * 0.4), int(n * 0.5)
    grid[lo:hi, lo:hi] = 0.005
    for _ in range(num_iterations):
        grid = evolve_np(grid, 0.1)
    return grid


def main():
    # Correctness: all three variants run the identical algorithm.
    py = np.asarray(run_py(ITERS, GRID))
    pyp = np.asarray(run_py_prealloc(ITERS, GRID))
    nped = run_np(ITERS, GRID)
    assert np.allclose(py, nped), "pure Python and numpy diverged!"
    assert np.allclose(py, pyp), "pure Python alloc vs prealloc diverged!"
    print(f"All three variants agree after {ITERS} iterations "
          f"(max abs diff {np.max(np.abs(py - nped)):.2e})")

    t_py = time_s(lambda: run_py(ITERS, GRID), number=1, repeat=3)
    t_pyp = time_s(lambda: run_py_prealloc(ITERS, GRID), number=1, repeat=3)
    t_np = time_s(lambda: run_np(ITERS, GRID), number=1, repeat=3)
    print(f"\n{GRID}x{GRID} grid, {ITERS} iterations:")
    print(f"  pure Python (alloc/iter): {t_py * 1e3:8.1f} ms   peak {human(peak_bytes(lambda: run_py(ITERS, GRID)))}")
    print(f"  pure Python (prealloc):   {t_pyp * 1e3:8.1f} ms   peak {human(peak_bytes(lambda: run_py_prealloc(ITERS, GRID)))}")
    print(f"  numpy:                    {t_np * 1e3:8.1f} ms   peak {human(peak_bytes(lambda: run_np(ITERS, GRID)))}")
    print(f"  -> preallocating the output buffer gives a small win ({t_py / t_pyp:.2f}x): one")
    print("     fewer grid allocation per iteration. But it can't fix pointer fragmentation,")
    print(f"     so numpy still wins big (~{t_py / t_np:.0f}x): contiguous typed memory + vectorized C.")


if __name__ == "__main__":
    main()
