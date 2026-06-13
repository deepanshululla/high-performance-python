"""Julia set generator — vectorized with numpy.

Same computation and result as julia_set.py (the pure-Python version), but the
per-point escape-time loop is replaced with whole-array numpy operations: each
of the `maxiter` passes advances *all* still-active points at once, so the
34-million-iteration Python loop collapses to ~300 vectorized steps.

Produces an identical output to the pure-Python version (the book's
1000x1000 @ 300 checksum, 33219980, still holds).
"""
import argparse
import time
from functools import wraps

import numpy as np


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
def calculate_z_numpy(maxiter, zs, cs):
    """Vectorized escape-time: advance every active point each pass.

    `output[k]` ends up equal to the number of iterations point k survived
    before |z| >= 2 (capped at maxiter) — identical to the scalar loop's `n`.
    """
    z = np.asarray(zs, dtype=np.complex128)
    c = np.asarray(cs, dtype=np.complex128)
    output = np.zeros(z.shape, dtype=np.int32)
    # Whole-array update each pass: no per-iteration fancy indexing. Escaped
    # points diverge to inf/nan, so `abs(z) < 2` stays False and they stop
    # contributing — `output += active` keeps the count identical to the loop's n.
    with np.errstate(over="ignore", invalid="ignore"):
        for _ in range(maxiter):
            active = np.abs(z) < 2
            output += active            # bool -> +1 for points still inside
            z = z * z + c               # advance ALL points (full array)
    return output


def calc_pure_python(desired_width, max_iterations):
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

    print(f"Length of x: {len(x)}")
    print(f"Total elements: {len(zs)}")

    output = calculate_z_numpy(max_iterations, zs, cs)

    # Same fixture as the pure-Python version — proves identical results.
    if desired_width == 1000 and max_iterations == 300:
        assert output.sum() == 33219980
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Julia set generator (numpy vectorized).")
    parser.add_argument("--width", type=int, default=1000, help="grid width (default: 1000)")
    parser.add_argument("--max-iterations", type=int, default=300, help="max iterations (default: 300)")
    args = parser.parse_args()
    calc_pure_python(desired_width=args.width, max_iterations=args.max_iterations)
