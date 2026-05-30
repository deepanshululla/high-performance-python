"""mprof memory timeline for the PURE-Python Julia set — no optimization.

Just the two natural phases of julia_set.py, labeled with the injected
TimeStamper context manager so they show as brackets on `mprof plot`:

    build_grid  -> build the zs / cs lists of 1,000,000 boxed complex objects
    compute     -> the scalar escape-time loop (34M iterations)

Unlike `@profile` (which traces every line and is ~15x slower), `mprof run`
only samples RSS every 0.1s, so the loop runs at full speed.

    uv run mprof run --python python chapter_2/mprof_julia_pure.py --width 1000
    MPLBACKEND=Agg uv run mprof plot --output chapter_2/mprof_julia_pure.png mprofile_*.dat
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


def build_grid(width):
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
    zs, cs = [], []
    for ycoord in y:
        for xcoord in x:
            zs.append(complex(xcoord, ycoord))
            cs.append(complex(C_REAL, C_IMAG))
    return zs, cs


def calculate_z_serial_purepython(maxiter, zs, cs):
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


def main(width, maxiter):
    # Single-token labels (mprof's .dat parser splits FUNC lines on whitespace).
    with profile.timestamp("build_grid"):
        zs, cs = build_grid(width)

    with profile.timestamp("compute"):
        output = calculate_z_serial_purepython(maxiter, zs, cs)

    if width == 1000 and maxiter == 300:
        assert sum(output) == 33219980
    print(f"done: sum={sum(output)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="mprof timeline, pure-Python Julia set.")
    parser.add_argument("--width", type=int, default=1000)
    parser.add_argument("--max-iterations", type=int, default=300)
    args = parser.parse_args()
    main(args.width, args.max_iterations)
