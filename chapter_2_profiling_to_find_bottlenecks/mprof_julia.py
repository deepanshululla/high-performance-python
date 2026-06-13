"""mprof time-series memory profiling with labeled phases (context manager).

`mprof run` samples the whole process's RSS over wall-clock time — a different
view from the per-line @profile table: it shows memory *as the program runs*.

To label regions of that timeline, `mprof run --python` injects a `profile`
object (a memory_profiler `TimeStamper`) into builtins, and
`profile.timestamp("label")` is a CONTEXT MANAGER that records a timestamped
band. `mprof plot` then draws each labeled block as a bracketed span on the
graph, so you can see which phase owns which memory.

    uv run mprof run --python python chapter_2/mprof_julia.py --width 1000
    uv run mprof plot --output chapter_2/mprof_julia.png    # render the graph
    uv run mprof peak                                       # just the peak number

Note: we do NOT `from memory_profiler import profile` — that is the line-profiler
decorator and would shadow the TimeStamper that mprof injects. Instead we use the
injected global, with a no-op fallback so the script still runs normally.
"""
import argparse
from contextlib import contextmanager

import numpy as np

try:
    profile  # type: ignore[used-before-def]  # injected by `mprof run --python`
except NameError:
    class _NoTimestamp:
        """No-op stand-in when not running under `mprof run --python`."""
        @contextmanager
        def timestamp(self, name="<block>"):
            yield
    profile = _NoTimestamp()


X1, X2, Y1, Y2 = -1.8, 1.8, -1.8, 1.8
C_REAL, C_IMAG = -0.62772, -0.42193


def build_lists(width):
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


def calculate_z_numpy(maxiter, z, c):
    output = np.zeros(z.shape, dtype=np.int32)
    with np.errstate(over="ignore", invalid="ignore"):
        for _ in range(maxiter):
            output += np.abs(z) < 2
            z = z * z + c
    return output


def main(width, maxiter):
    # Each `profile.timestamp(...)` block becomes a labeled bracket on the plot.
    # NOTE: labels must be a single token — mprof's .dat parser splits FUNC
    # lines on whitespace, so use underscores/hyphens, not spaces.
    with profile.timestamp("build_python_lists"):
        zs, cs = build_lists(width)

    with profile.timestamp("convert_to_numpy_arrays"):
        z = np.asarray(zs, dtype=np.complex128)
        c = np.asarray(cs, dtype=np.complex128)

    with profile.timestamp("free_python_lists"):
        del zs, cs

    with profile.timestamp("numpy_compute"):
        output = calculate_z_numpy(maxiter, z, c)

    if width == 1000 and maxiter == 300:
        assert output.sum() == 33219980
    print(f"done: sum={int(output.sum())}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="mprof labeled memory timeline.")
    parser.add_argument("--width", type=int, default=1000)
    parser.add_argument("--max-iterations", type=int, default=300)
    args = parser.parse_args()
    main(args.width, args.max_iterations)
