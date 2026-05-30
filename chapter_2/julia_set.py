"""Julia set generator — the canonical example from High Performance Python.

Computes the false-grayscale Julia set for the constant c = -0.62772 - 0.42193j
over a square region of the complex plane, using a pure-Python escape-time loop.
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


@timefn
def calculate_z_serial_purepython(maxiter, zs, cs):
    """Escape-time iteration: for each z, count steps until |z| > 2."""
    output = [0] * len(zs)
    for i in range(len(zs)):
        n = 0
        z = zs[i]
        c = cs[i]
        while abs(z) < 2 and n < maxiter:
            z = z * z + c
            n += 1
        output[i] = n
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

    output = calculate_z_serial_purepython(max_iterations, zs, cs)

    # Sanity check from the book: this sum is a fixture for 1000x1000 @ 300 iter.
    if desired_width == 1000 and max_iterations == 300:
        assert sum(output) == 33219980
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Julia set escape-time generator.")
    parser.add_argument("--width", type=int, default=1000, help="grid width (default: 1000)")
    parser.add_argument("--max-iterations", type=int, default=300, help="max iterations (default: 300)")
    args = parser.parse_args()
    calc_pure_python(desired_width=args.width, max_iterations=args.max_iterations)