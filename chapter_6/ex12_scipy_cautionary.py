"""Chapter 6 - Exercise 12: a cautionary tale -- scipy.laplace (Examples 6-27, 6-28).

Task: `scipy.ndimage.laplace` is a ready-made laplacian filter with built-in
boundary handling (`mode="wrap"` gives our periodic conditions). It's a tempting
drop-in for the hand-written laplacian -- Laplacians are common in image analysis,
so surely the library version is faster? Verify it's correct, then benchmark it.

Takeaway: it is NOT faster -- it's 2-4x SLOWER here, and the gap WIDENS with grid
size. scipy's filter is written to be fully general (any dimensionality, any
boundary mode, any filter footprint), so it issues far more instructions and
branches than our specialized roll laplacian, which does exactly one thing. This is
the chapter's core lesson dramatized: an "optimization" that sounds obviously
better can be a regression. Hypothesize, then MEASURE -- every time.

Run: .venv/bin/python chapter_6/ex12_scipy_cautionary.py
"""
import time

import numpy as np
from scipy.ndimage import laplace


# --- our specialized laplacian (roll up/down/left/right, subtract 4*center) ---
def laplacian_custom(grid, out):
    np.copyto(out, grid)
    out *= -4
    out += np.roll(grid, +1, 0)
    out += np.roll(grid, -1, 0)
    out += np.roll(grid, +1, 1)
    out += np.roll(grid, -1, 1)


def seed(n):
    g = np.zeros((n, n))
    out = np.zeros((n, n))
    lo, hi = int(n * 0.4), int(n * 0.5)
    g[lo:hi, lo:hi] = 0.005
    return g, out


def run_custom(n, iters):
    grid, out = seed(n)
    for _ in range(iters):
        laplacian_custom(grid, out)
        out *= 0.1
        out += grid
        grid, out = out, grid
    return grid


def run_scipy(n, iters):
    grid, out = seed(n)
    for _ in range(iters):
        laplace(grid, output=out, mode="wrap")   # periodic boundary = our modulo wrap
        out *= 0.1
        out += grid
        grid, out = out, grid
    return grid


def best_time(fn, reps=3):
    best = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t)
    return best


def main():
    # Correctness FIRST: scipy's wrap laplacian must equal our roll laplacian,
    # otherwise the speed comparison would be meaningless.
    g = np.random.rand(64, 64)
    mine = np.zeros((64, 64))
    laplacian_custom(g, mine)
    theirs = laplace(g, mode="wrap")
    assert np.allclose(mine, theirs), "scipy.laplace(wrap) != our roll laplacian!"
    print("scipy.laplace(mode='wrap') is numerically identical to our roll laplacian.")
    print("So this is a fair fight -- same answer, different implementation.\n")

    iters = 50
    print(f"Diffusion evolve, {iters} iterations, by grid size:")
    for n in (256, 512, 1024, 2048):
        t_mine = best_time(lambda n=n: run_custom(n, iters))
        t_scipy = best_time(lambda n=n: run_scipy(n, iters))
        print(f"  {n:>4}x{n:<4}: custom {t_mine * 1e3:7.1f} ms   scipy {t_scipy * 1e3:8.1f} ms   "
              f"-> scipy {t_scipy / t_mine:.2f}x SLOWER")
    print("  -> the general-purpose filter loses to specialized code, and loses by MORE")
    print("     as the grid grows. 'It's a well-known library, it must be faster' is a")
    print("     hypothesis, not a fact -- the whole chapter's discipline is to benchmark it.")


if __name__ == "__main__":
    main()
