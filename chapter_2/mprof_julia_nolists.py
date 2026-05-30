"""mprof memory timeline for the no-lists Julia set (coordinates computed inline).

Compare against mprof_julia_pure.py: the `build_grid` phase that cost ~80 MiB
there is gone — we only build the tiny axes, so the whole program stays near the
output list's footprint.

    uv run mprof run --python python chapter_2/mprof_julia_nolists.py --width 1000
    MPLBACKEND=Agg uv run mprof plot --output chapter_2/mprof_julia_nolists.png mprofile_*.dat
"""
import argparse
from contextlib import contextmanager

from julia_set_nolists import build_axes, calculate_z_serial_purepython

try:
    profile  # type: ignore[used-before-def]  # injected by `mprof run --python`
except NameError:
    class _NoTimestamp:
        @contextmanager
        def timestamp(self, name="<block>"):
            yield
    profile = _NoTimestamp()


def main(width, maxiter):
    with profile.timestamp("build_axes"):
        x, y = build_axes(width)        # only 2 * 1000 floats — a few KB

    with profile.timestamp("compute_inline"):
        output = calculate_z_serial_purepython.__wrapped__(maxiter, x, y)

    if width == 1000 and maxiter == 300:
        assert sum(output) == 33219980
    print(f"done: sum={sum(output)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="mprof timeline, no-lists Julia set.")
    parser.add_argument("--width", type=int, default=1000)
    parser.add_argument("--max-iterations", type=int, default=300)
    args = parser.parse_args()
    main(args.width, args.max_iterations)
