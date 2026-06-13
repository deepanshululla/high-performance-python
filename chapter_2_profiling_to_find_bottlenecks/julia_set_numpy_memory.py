"""Memory footprint of the numpy version vs. the pure-Python version.

Two functions are decorated with memory_profiler's @profile:

  * calc_pure_python_lists  — builds Python lists, then np.asarray() converts
    them (the current julia_set_numpy.py approach). Both the lists AND the
    arrays exist at peak, so this does NOT save memory by itself.

  * calc_pure_python_direct — builds the complex grid directly as numpy arrays
    with meshgrid (no intermediate Python lists). This is the real win.

Run:
    uv run python -m memory_profiler chapter_2/julia_set_numpy_memory.py --width 1000
"""
import argparse
import time
from functools import wraps

import numpy as np
from memory_profiler import profile


X1, X2, Y1, Y2 = -1.8, 1.8, -1.8, 1.8
C_REAL, C_IMAG = -0.62772, -0.42193


def timefn(fn):
    @wraps(fn)
    def measure_time(*args, **kwargs):
        t1 = time.time()
        result = fn(*args, **kwargs)
        t2 = time.time()
        print(f"@timefn: {fn.__name__} took {t2 - t1:.4f} seconds")
        return result
    return measure_time


@timefn
def calculate_z_numpy(maxiter, z, c):
    """Vectorized escape-time on numpy arrays (no per-point Python loop)."""
    output = np.zeros(z.shape, dtype=np.int32)
    with np.errstate(over="ignore", invalid="ignore"):
        for _ in range(maxiter):
            active = np.abs(z) < 2
            output += active
            z = z * z + c
    return output


@profile
def calc_pure_python_lists(desired_width, max_iterations):
    """numpy compute, but the grid is built as Python lists then converted."""
    x_step = (X2 - X1) / desired_width
    y_step = (Y1 - Y2) / desired_width
    x, y = [], []
    ycoord = Y2
    while ycoord > Y1:
        y.append(ycoord)
        ycoord += y_step
    xcoord = X1
    while xcoord < X2:
        x.append(xcoord)
        xcoord += x_step

    zs, cs = [], []
    for ycoord in y:
        for xcoord in x:
            zs.append(complex(xcoord, ycoord))
            cs.append(complex(C_REAL, C_IMAG))

    z = np.asarray(zs, dtype=np.complex128)        # array now exists alongside the list
    c = np.asarray(cs, dtype=np.complex128)
    output = calculate_z_numpy(max_iterations, z, c)
    return output


@profile
def calc_pure_python_direct(desired_width, max_iterations):
    """Build the complex grid directly as numpy arrays — no Python lists."""
    xs = np.linspace(X1, X2, desired_width, endpoint=False)
    ys = np.linspace(Y2, Y1, desired_width, endpoint=False)
    xv, yv = np.meshgrid(xs, ys)
    z = (xv + 1j * yv).ravel().astype(np.complex128)      # the whole grid, one array
    c = np.full(z.shape, complex(C_REAL, C_IMAG), dtype=np.complex128)
    output = calculate_z_numpy(max_iterations, z, c)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="numpy Julia set memory comparison.")
    parser.add_argument("--width", type=int, default=1000, help="grid width (default: 1000)")
    parser.add_argument("--max-iterations", type=int, default=300)
    parser.add_argument("--mode", choices=["lists", "direct", "both"], default="both")
    args = parser.parse_args()

    if args.mode in ("lists", "both"):
        print("\n### list-built grid + np.asarray ###")
        out = calc_pure_python_lists(args.width, args.max_iterations)
        if args.width == 1000 and args.max_iterations == 300:
            assert out.sum() == 33219980
    if args.mode in ("direct", "both"):
        print("\n### direct numpy grid (meshgrid) ###")
        out = calc_pure_python_direct(args.width, args.max_iterations)
        if args.width == 1000 and args.max_iterations == 300:
            assert out.sum() == 33219980
