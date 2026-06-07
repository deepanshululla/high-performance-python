"""Chapter 6 - Summary benchmark: runtime + speedup sweep (Tables 6-1 and 6-2).

Reproduces the chapter's two summary tables -- total runtime of every
implementation across grid sizes, and speedup vs naive pure Python -- for the
implementations available here (numexpr/scipy are not installed):

    python            pure Python, fresh grid each iter        (ex02)
    python+prealloc   pure Python, reused scratch + swap        (ex02 / Example 6-6)
    numpy             roll laplacian, allocates each iter       (ex02 / ex04)
    numpy+inplace     copyto + in-place += with scratch swap    (ex04)
    numpy+roll_add    custom in-place roll_add laplacian        (ex05)
    numpy+numexpr     compiled, cache-aware combine step        (ex11)   [if installed]
    numpy+scipy       scipy.ndimage.laplace (general filter)    (ex12)   [if installed]
    torch (mps)       GPU roll laplacian                        (ex07)
    torch+conv (mps)  GPU 3x3 convolution laplacian             (ex09)

Differences from the book's tables (stated up front, not hidden):
  * ITERS is small (default 50), not the book's 1,000 -- pure Python at 512x512 x
    1,000 would take over an hour. Speedups are ratios, so they stay comparable.
  * Pure Python is only MEASURED up to PY_MAX_GRID; above that its baseline is
    EXTRAPOLATED (it is cleanly O(n^2 * iters)) and tagged "~" so the speedup
    column still spans every size, exactly like the book's Table 6-2.
  * GPU is Apple MPS, not NVIDIA CUDA -- magnitudes differ.

Run: .venv/bin/python chapter_6/bench_summary.py
     .venv/bin/python chapter_6/bench_summary.py 30 64,128,256,512   # iters, sizes
"""
import sys
import time

import numpy as np

try:
    import torch
    HAVE_TORCH = torch.backends.mps.is_available() or torch.cuda.is_available()
    DEVICE = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else None)
    SYNC = (torch.mps.synchronize if DEVICE == "mps"
            else torch.cuda.synchronize if DEVICE == "cuda" else (lambda: None))
except ModuleNotFoundError:
    HAVE_TORCH, DEVICE, SYNC = False, None, (lambda: None)

try:
    import numexpr as ne
    HAVE_NUMEXPR = True
except ModuleNotFoundError:
    HAVE_NUMEXPR = False

try:
    from scipy.ndimage import laplace as scipy_laplace
    HAVE_SCIPY = True
except ModuleNotFoundError:
    HAVE_SCIPY = False

ITERS = 50
SIZES = (64, 128, 256, 512)
PY_MAX_GRID = 256        # measure pure Python only up to here; extrapolate beyond


# ---- pure Python -------------------------------------------------------------
def _evolve_py(grid, dt, out, n, D=1.0):
    for i in range(n):
        for j in range(n):
            gxx = grid[(i + 1) % n][j] + grid[(i - 1) % n][j] - 2.0 * grid[i][j]
            gyy = grid[i][(j + 1) % n] + grid[i][(j - 1) % n] - 2.0 * grid[i][j]
            out[i][j] = grid[i][j] + D * (gxx + gyy) * dt


def _seed_py(n):
    g = [[0.0] * n for _ in range(n)]
    lo, hi = int(n * 0.4), int(n * 0.5)
    for i in range(lo, hi):
        for j in range(lo, hi):
            g[i][j] = 0.005
    return g


def run_python(n, iters):
    grid = _seed_py(n)
    for _ in range(iters):
        nxt = [[0.0] * n for _ in range(n)]      # fresh allocation every iteration
        _evolve_py(grid, 0.1, nxt, n)
        grid = nxt
    return grid


def run_python_prealloc(n, iters):
    grid, nxt = _seed_py(n), [[0.0] * n for _ in range(n)]
    for _ in range(iters):
        _evolve_py(grid, 0.1, nxt, n)
        grid, nxt = nxt, grid
    return grid


# ---- numpy -------------------------------------------------------------------
def _seed_np(n):
    g = np.zeros((n, n))
    lo, hi = int(n * 0.4), int(n * 0.5)
    g[lo:hi, lo:hi] = 0.005
    return g


def run_numpy(n, iters):
    g = _seed_np(n)
    for _ in range(iters):
        lap = (np.roll(g, 1, 0) + np.roll(g, -1, 0)
               + np.roll(g, 1, 1) + np.roll(g, -1, 1) - 4 * g)
        g = g + 0.1 * lap
    return g


def run_numpy_inplace(n, iters):
    g, out = _seed_np(n), np.zeros((n, n))
    for _ in range(iters):
        np.copyto(out, g)
        out *= -4
        out += np.roll(g, 1, 0)
        out += np.roll(g, -1, 0)
        out += np.roll(g, 1, 1)
        out += np.roll(g, -1, 1)
        out *= 0.1
        out += g
        g, out = out, g
    return g


def _roll_add(rollee, shift, axis, out):
    if shift == 1 and axis == 0:
        out[1:, :] += rollee[:-1, :]; out[0, :] += rollee[-1, :]
    elif shift == -1 and axis == 0:
        out[:-1, :] += rollee[1:, :]; out[-1, :] += rollee[0, :]
    elif shift == 1 and axis == 1:
        out[:, 1:] += rollee[:, :-1]; out[:, 0] += rollee[:, -1]
    elif shift == -1 and axis == 1:
        out[:, :-1] += rollee[:, 1:]; out[:, -1] += rollee[:, 0]


def run_numpy_roll_add(n, iters):
    g, out = _seed_np(n), np.zeros((n, n))
    for _ in range(iters):
        np.copyto(out, g)
        out *= -4
        _roll_add(g, 1, 0, out)
        _roll_add(g, -1, 0, out)
        _roll_add(g, 1, 1, out)
        _roll_add(g, -1, 1, out)
        out *= 0.1
        out += g
        g, out = out, g
    return g


def _lap_inplace(g, out):
    np.copyto(out, g)
    out *= -4
    out += np.roll(g, 1, 0)
    out += np.roll(g, -1, 0)
    out += np.roll(g, 1, 1)
    out += np.roll(g, -1, 1)


def run_numpy_numexpr(n, iters):
    g, out = _seed_np(n), np.zeros((n, n))
    for _ in range(iters):
        _lap_inplace(g, out)
        ne.evaluate("out * 0.1 + g", out=out)
        g, out = out, g
    return g


def run_numpy_scipy(n, iters):
    g, out = _seed_np(n), np.zeros((n, n))
    for _ in range(iters):
        scipy_laplace(g, output=out, mode="wrap")
        out *= 0.1
        out += g
        g, out = out, g
    return g


# ---- torch (GPU) -------------------------------------------------------------
def run_torch(n, iters):
    g = torch.zeros((n, n), device=DEVICE)
    lo, hi = int(n * 0.4), int(n * 0.5)
    g[lo:hi, lo:hi] = 0.005
    for _ in range(iters):
        lap = (torch.roll(g, 1, 0) + torch.roll(g, -1, 0)
               + torch.roll(g, 1, 1) + torch.roll(g, -1, 1) - 4 * g)
        g = g + 0.1 * lap
    SYNC()
    return g


def _make_conv():
    k = torch.as_tensor([[0., 1., 0.], [1., -4., 1.], [0., 1., 0.]]).broadcast_to(1, 1, 3, 3).to(DEVICE)
    c = torch.nn.Conv2d(1, 1, 3, bias=False, padding_mode="circular", padding=1).to(DEVICE)
    c.weight = torch.nn.Parameter(k)
    return c


def run_torch_conv(n, iters):
    c = _make_conv()
    g = torch.zeros((1, 1, n, n), device=DEVICE)
    lo, hi = int(n * 0.4), int(n * 0.5)
    g[0, 0, lo:hi, lo:hi] = 0.005
    with torch.no_grad():
        for _ in range(iters):
            g = g + 0.1 * c(g)
    SYNC()
    return g


def best_time(fn, reps=3, warmup=0):
    for _ in range(warmup):
        fn()
    best = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t)
    return best


def main():
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else ITERS
    sizes = tuple(int(x) for x in sys.argv[2].split(",")) if len(sys.argv) > 2 else SIZES
    print(f"Diffusion benchmark: {iters} iterations per run, device={DEVICE or 'none (CPU only)'}\n")

    rows = [
        ("python", run_python, "cpu"),
        ("python+prealloc", run_python_prealloc, "cpu"),
        ("numpy", run_numpy, "cpu"),
        ("numpy+inplace", run_numpy_inplace, "cpu"),
        ("numpy+roll_add", run_numpy_roll_add, "cpu"),
    ]
    if HAVE_NUMEXPR:
        rows.append(("numpy+numexpr", run_numpy_numexpr, "cpu"))
    if HAVE_SCIPY:
        rows.append(("numpy+scipy", run_numpy_scipy, "cpu"))
    if HAVE_TORCH:
        rows += [("torch (%s)" % DEVICE, run_torch, "gpu"),
                 ("torch+conv (%s)" % DEVICE, run_torch_conv, "gpu")]

    # measure: times[label][n] = seconds (or None if skipped). py_percell calibrates
    # the extrapolated baseline for pure Python above PY_MAX_GRID.
    times = {label: {} for label, _, _ in rows}
    py_percell = None
    for n in sizes:
        for label, fn, kind in rows:
            if label.startswith("python") and n > PY_MAX_GRID:
                times[label][n] = None            # too slow to measure; extrapolate later
                continue
            warm = 1 if kind == "gpu" else 0
            t = best_time(lambda fn=fn, n=n: fn(n, iters), reps=3, warmup=warm)
            times[label][n] = t
            if label == "python":
                py_percell = t / (n * n * iters)  # cleanly O(n^2 * iters)

    # baseline for speedup = pure python (measured where possible, else extrapolated).
    def py_baseline(n):
        t = times["python"].get(n)
        if t is not None:
            return t, False
        return py_percell * n * n * iters, True     # estimated

    col = max(len(l) for l, _, _ in rows) + 1
    hdr = "  ".join(f"{n:>9}" for n in sizes)
    print(f"RUNTIME (seconds){'':<{col-16}}{hdr}")
    for label, _, _ in rows:
        cells = []
        for n in sizes:
            t = times[label][n]
            cells.append("       --" if t is None else f"{t:9.4f}")
        print(f"{label:<{col}}" + "  ".join(cells))

    print(f"\nSPEEDUP vs pure Python  ('~' = baseline extrapolated){'':<{max(0, col-52)}}")
    print(f"{'':<{col}}" + "  ".join(f"{n:>9}" for n in sizes))
    for label, _, _ in rows:
        cells = []
        for n in sizes:
            t = times[label][n]
            base, est = py_baseline(n)
            if t is None:
                cells.append("       --")
            else:
                cells.append(("~" if est else " ") + f"{base / t:7.1f}x")
        print(f"{label:<{col}}" + "  ".join(cells))

    print("\nNotes: iters < book's 1000 (ratios still comparable); pure Python")
    print(f"  measured to {PY_MAX_GRID}x{PY_MAX_GRID}, extrapolated (~) above; GPU is {DEVICE}, not CUDA.")


if __name__ == "__main__":
    main()
