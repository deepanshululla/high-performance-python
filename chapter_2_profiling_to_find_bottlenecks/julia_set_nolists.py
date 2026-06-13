"""Julia set — simplified: no zs/cs lists, coordinates computed in the loop.

The original builds two 1,000,000-element lists (`zs`, `cs`) of boxed complex
objects up front (~81 MiB). Here we keep only the two coordinate *axes* (`x` and
`y`, 1000 points each — a few KB) and compute `complex(xcoord, ycoord)` and the
constant `c` directly inside calculate_z_serial_purepython. Exactly the same work
is performed; we just don't store the grid. The only large allocation left is the
`output` list of escape counts.

Result is identical to julia_set.py (checksum 33219980).
"""
import argparse
import time
from functools import wraps


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


def build_axes(desired_width):
    """Just the two 1D coordinate axes — not the full grid."""
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
    return x, y


@timefn
def calculate_z_serial_purepython(maxiter, x, y):
    """Escape-time loop; z and c are computed inline, not read from lists."""
    output = []
    c = complex(C_REAL, C_IMAG)            # the constant, computed once
    for ycoord in y:
        for xcoord in x:
            z = complex(xcoord, ycoord)    # computed here, not stored in a list
            n = 0
            while abs(z) < 2 and n < maxiter:
                z = z * z + c
                n += 1
            output.append(n)
    return output


def calc_pure_python(desired_width, max_iterations):
    x, y = build_axes(desired_width)
    print(f"Length of x: {len(x)}")
    print(f"Total elements: {len(x) * len(y)}")

    output = calculate_z_serial_purepython(max_iterations, x, y)

    if desired_width == 1000 and max_iterations == 300:
        assert sum(output) == 33219980    # identical result to julia_set.py
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Julia set (no zs/cs lists).")
    parser.add_argument("--width", type=int, default=1000)
    parser.add_argument("--max-iterations", type=int, default=300)
    args = parser.parse_args()
    calc_pure_python(desired_width=args.width, max_iterations=args.max_iterations)
