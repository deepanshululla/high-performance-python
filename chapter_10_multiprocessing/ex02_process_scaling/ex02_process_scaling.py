"""ex02 — how far does adding processes actually take us?

ex01 showed that 4 processes beat 1. Here we sweep the worker count from 1 up
past the core count and plot speedup against the ideal n-times line. The Monte
Carlo workload is perfectly even, so this is the friendliest possible case for
linear scaling — any shortfall is pure overhead, not load imbalance.

The book runs on an 8-physical-core laptop *with* hyperthreading and sees the
speedup flatten hard past 8 because the 8 hyperthreads share silicon. This
machine has 10 physical cores and **no** hyperthreading, so we expect a cleaner
story: near-linear up to ~10 workers, then a flat (even slightly worse) line as
extra processes just contend for the same 10 cores and steal time from the OS.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[0]))

from perf import time_s  # noqa: E402
from _pi import estimate_pure, pi_from_counts, assert_pi, TOTAL_DARTS  # noqa: E402
from _mp import CTX, N_PHYSICAL  # noqa: E402

WORKER_COUNTS = [1, 2, 4, 6, 8, 10, 12, 16]


def run_with(workers, total=TOTAL_DARTS):
    per = total // workers
    with CTX.Pool(workers) as pool:
        counts = pool.map(estimate_pure, [per] * workers)
    return assert_pi(pi_from_counts(counts, per * workers))


def sweep(worker_counts=WORKER_COUNTS, total=TOTAL_DARTS):
    """Return [(workers, seconds), ...] for the pure-Python pi job."""
    rows = []
    for w in worker_counts:
        rows.append((w, time_s(lambda w=w: run_with(w, total), number=1, repeat=1)))
    return rows


def main():
    rows = sweep()
    base = rows[0][1]
    print(f"pure-Python pi scaling, {TOTAL_DARTS:,} darts "
          f"({N_PHYSICAL} physical cores, no hyperthreading)")
    for w, t in rows:
        print(f"  {w:>2} proc : {t:6.2f}s   speedup {base / t:5.2f}x   "
              f"efficiency {100 * base / t / w:5.1f}%")


if __name__ == "__main__":
    main()
