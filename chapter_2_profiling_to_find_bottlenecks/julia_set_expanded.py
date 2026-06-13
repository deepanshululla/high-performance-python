"""Julia set generator — compound `while` broken into individual statements.

Same computation as julia_set.py, but the single line

    while abs(z) < 2 and n < maxiter:

is expanded into separate statements so line_profiler can record the cost of
each part of the original condition independently (High Performance Python,
Example 2-10). This is purely a measurement aid — it is *slower* than the
compact form because of the extra per-iteration bookkeeping; the point is to
see where the time goes, not to optimise.
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
    """Escape-time iteration with the compound condition split apart.

    Each sub-expression of `abs(z) < 2 and n < maxiter` lands on its own
    line so a line profiler can attribute time to it separately.
    """
    output = [0] * len(zs)
    for i in range(len(zs)):
        n = 0
        z = zs[i]
        c = cs[i]
        while True:
            not_yet_escaped = abs(z) < 2      # cost of the magnitude test
            iterations_left = n < maxiter     # cost of the counter test
            if not_yet_escaped and iterations_left:
                z = z * z + c
                n += 1
            else:
                break
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
    parser = argparse.ArgumentParser(description="Julia set generator (expanded while).")
    parser.add_argument("--width", type=int, default=1000, help="grid width (default: 1000)")
    parser.add_argument("--max-iterations", type=int, default=300, help="max iterations (default: 300)")
    args = parser.parse_args()
    calc_pure_python(desired_width=args.width, max_iterations=args.max_iterations)
