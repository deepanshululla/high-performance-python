"""Chapter 6 - Exercise 11: numexpr and the cache crossover (Examples 6-18, 6-19).

Task: rewrite the in-place numpy evolve's final combine step `out*0.1 + grid` as a
single compiled `numexpr.evaluate("out*0.1 + grid", out=out)`, and sweep grid sizes
to find where numexpr starts to win.

numexpr compiles a whole vector expression into one cache-aware pass: it chunks the
arrays so the pieces it's working on stay in CPU cache, fuses the multiply+add (no
temporary), and can use multiple cores. numpy instead evaluates one operation at a
time, materializing an intermediate between each.

Takeaway: numexpr is a NET LOSS on small grids -- the string compile + chunking +
thread overhead isn't repaid when the data already fits in cache. It only wins once
the arrays overflow the last-level cache (~1000x1000 doubles on a typical L3), where
its cache-juggling avoids the memory-bandwidth stalls that hurt plain numpy. So the
"optimization" is entirely size-dependent -- exactly the kind of claim you must
benchmark, not assume.

Run: .venv/bin/python chapter_6/ex11_numexpr_crossover.py
"""
import time

import numexpr as ne
import numpy as np


def laplacian_inplace(grid, out):
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


def run_numpy(n, iters):
    grid, out = seed(n)
    for _ in range(iters):
        laplacian_inplace(grid, out)
        out *= 0.1                      # two separate numpy passes:
        out += grid                     #   multiply, then add (temporary between)
        grid, out = out, grid
    return grid


def run_numexpr(n, iters):
    grid, out = seed(n)
    for _ in range(iters):
        laplacian_inplace(grid, out)
        ne.evaluate("out * 0.1 + grid", out=out)   # one compiled, fused, cache-aware pass
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
    iters = 50
    print(f"numexpr cores available: {ne.detect_number_of_cores()} "
          f"(numexpr uses {ne.nthreads} threads)")

    # Correctness: same algorithm, same grid.
    a = run_numpy(128, iters)
    b = run_numexpr(128, iters)
    assert np.allclose(a, b), "numpy and numexpr diverged!"
    print(f"numpy and numexpr agree (max abs diff {np.max(np.abs(a - b)):.2e})\n")

    print(f"Diffusion evolve, {iters} iterations, by grid size:")
    crossover = None
    for n in (256, 512, 1024, 2048):
        t_np = best_time(lambda n=n: run_numpy(n, iters))
        t_ne = best_time(lambda n=n: run_numexpr(n, iters))
        winner = "numexpr" if t_ne < t_np else "numpy"
        if winner == "numexpr" and crossover is None:
            crossover = n
        ratio = max(t_np, t_ne) / min(t_np, t_ne)
        print(f"  {n:>4}x{n:<4}: numpy {t_np * 1e3:7.1f} ms   numexpr {t_ne * 1e3:7.1f} ms   "
              f"-> {winner} faster ({ratio:.2f}x)")
    if crossover:
        print(f"  -> numexpr overtakes numpy at ~{crossover}x{crossover}: once two grids no longer")
        print("     fit in the last-level cache, numexpr's cache-aware chunking pays off.")
    else:
        print("  -> numexpr never overtook numpy in this range; the arrays still fit in cache.")
    print("     Below the crossover, the compile + threading overhead makes numexpr a net loss.")


if __name__ == "__main__":
    main()
