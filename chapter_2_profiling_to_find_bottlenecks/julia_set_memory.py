"""Julia set — memory-profiled with `memory_profiler`'s @profile decorator.

Unlike line_profiler (which can autoprofile), memory_profiler requires an
explicit `@profile` decorator on the function you want to inspect. Each line of
the decorated function is annotated with the process memory *before* it ran and
the *increment* that line caused.

`calc_pure_python` is decorated here because that's where the memory actually
grows: building the two 1,000,000-element `zs` / `cs` lists (each complex number
is a separate Python object) is what pushes RSS toward ~130 MB.

Run it (decorated functions are profiled automatically under this module):
    uv run python -m memory_profiler chapter_2/julia_set_memory.py --width 1000

memory_profiler is slow (it samples RSS on every line of the decorated
function), so use a smaller --width for a quick look:
    uv run python -m memory_profiler chapter_2/julia_set_memory.py --width 300
"""
import argparse
import time
from functools import wraps

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
def calculate_z_serial_purepython(maxiter, zs, cs):
    """Escape-time iteration (undecorated: runs at full speed)."""
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


@profile
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

    # The two big allocations: 1M complex objects each.
    zs, cs = [], []
    for ycoord in y:
        for xcoord in x:
            zs.append(complex(xcoord, ycoord))
            cs.append(complex(C_REAL, C_IMAG))

    print(f"Length of x: {len(x)}")
    print(f"Total elements: {len(zs)}")

    output = calculate_z_serial_purepython(max_iterations, zs, cs)

    if desired_width == 1000 and max_iterations == 300:
        assert sum(output) == 33219980
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Julia set generator (memory-profiled).")
    parser.add_argument("--width", type=int, default=1000, help="grid width (default: 1000)")
    parser.add_argument("--max-iterations", type=int, default=300, help="max iterations (default: 300)")
    args = parser.parse_args()
    calc_pure_python(desired_width=args.width, max_iterations=args.max_iterations)
