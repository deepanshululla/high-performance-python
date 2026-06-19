"""A self-contained CPU+memory workload, run identically on the host and inside a
container. Mirrors the book's Example 11-6 (a numpy 2D diffusion), but carries its
own internal timer so we measure *compute* time, not container startup, and prints
a checksum so a container that somehow computed the wrong thing would be caught.

Deliberately has no dependency on the repo (only numpy) so the exact same file
runs under the host venv and inside the slim python image.
"""
import time

import numpy as np

GRID_N = 768
ITERS = 400
DT = 0.1


def diffusion(grid_n=GRID_N, iters=ITERS):
    g = np.zeros((grid_n, grid_n))
    g[grid_n // 4:3 * grid_n // 4, grid_n // 4:3 * grid_n // 4] = 1.0
    for _ in range(iters):
        lap = (-4 * g + np.roll(g, 1, 0) + np.roll(g, -1, 0)
               + np.roll(g, 1, 1) + np.roll(g, -1, 1))
        g = g + DT * lap
    return float(g.sum())


if __name__ == "__main__":
    t0 = time.perf_counter()
    total = diffusion()
    runtime = time.perf_counter() - t0
    # Machine-readable lines the driver parses; mass is conserved by the roll
    # Laplacian, so the sum equals the initial hot-square area exactly.
    print(f"RUNTIME_S {runtime:.4f}")
    print(f"SUM {total:.1f}")
