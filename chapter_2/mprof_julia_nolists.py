"""mprof memory timeline for the no-lists Julia set (coordinates computed inline).

Self-contained (no imports from the other modules). Compare against
mprof_julia_pure.py: the `build_grid` phase that cost ~80 MiB there is gone — we
only build the tiny axes, so the whole program stays near the output list's
footprint (~40 MiB peak vs. ~136 MiB).

    uv run mprof run --python python chapter_2/mprof_julia_nolists.py --width 1000
    MPLBACKEND=Agg uv run mprof plot --output chapter_2/mprof_julia_nolists.png mprofile_*.dat
"""
import argparse
from contextlib import contextmanager

try:
    profile  # type: ignore[used-before-def]  # injected by `mprof run --python`
except NameError:
    class _NoTimestamp:
        @contextmanager
        def timestamp(self, name="<block>"):
            yield
    profile = _NoTimestamp()


X1, X2, Y1, Y2 = -1.8, 1.8, -1.8, 1.8
C_REAL, C_IMAG = -0.62772, -0.42193


def build_axes(width):
    """Just the two 1D coordinate axes (1000 floats each) — not the full grid."""
    x_step = (X2 - X1) / width
    y_step = (Y1 - Y2) / width
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


def calculate_z_inline(maxiter, x, y):
    """Escape-time loop; z and c are computed inline, not read from lists."""
    output = []
    c = complex(C_REAL, C_IMAG)
    for ycoord in y:
        for xcoord in x:
            z = complex(xcoord, ycoord)    # created here, never stored in a list
            n = 0
            while abs(z) < 2 and n < maxiter:
                z = z * z + c
                n += 1
            output.append(n)
    return output


def main(width, maxiter):
    with profile.timestamp("build_axes"):
        x, y = build_axes(width)           # a few KB, not ~80 MiB

    with profile.timestamp("compute_inline"):
        output = calculate_z_inline(maxiter, x, y)

    if width == 1000 and maxiter == 300:
        assert sum(output) == 33219980
    print(f"done: sum={sum(output)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="mprof timeline, no-lists Julia set.")
    parser.add_argument("--width", type=int, default=1000)
    parser.add_argument("--max-iterations", type=int, default=300)
    args = parser.parse_args()
    main(args.width, args.max_iterations)
