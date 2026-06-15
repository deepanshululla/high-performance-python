"""ex03 — the same pi job in numpy: now threads help too.

We repeat ex01's serial/threads/processes comparison, but with the vectorised
`numpy` estimator. Two things change, and both are the point:

1. numpy is dramatically faster than the pure-Python loop for the same dart
   count, because it works on contiguous C arrays instead of millions of boxed
   Python floats.

2. *Threads now give a real speedup.* The array arithmetic (xs*xs + ys*ys <= 1)
   runs in C with the GIL released, so multiple threads genuinely overlap — the
   exact thing that was impossible in ex01. Processes still scale too.

The seed matters: each forked numpy worker inherits the parent's RNG state, so
`estimate_numpy` calls `np.random.seed()` to give every process a fresh stream.
Forget it and the workers silently draw identical sequences — the program looks
fine but the extra workers add no new information.
"""
import pathlib
import sys
from multiprocessing.dummy import Pool as ThreadPool

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[0]))

from perf import time_s  # noqa: E402
from _pi import (  # noqa: E402
    estimate_numpy, estimate_pure, pi_from_counts, assert_pi, NUMPY_DARTS, TOTAL_DARTS,
)
from _mp import CTX  # noqa: E402

WORKERS = 8   # the M1 Max has 8 performance cores; threads vs processes at that width


def run_serial(total=NUMPY_DARTS):
    return assert_pi(pi_from_counts([estimate_numpy(total)], total))


def run_threads(workers=WORKERS, total=NUMPY_DARTS):
    per = total // workers
    with ThreadPool(workers) as pool:
        counts = pool.map(estimate_numpy, [per] * workers)
    return assert_pi(pi_from_counts(counts, per * workers))


def run_processes(workers=WORKERS, total=NUMPY_DARTS):
    per = total // workers
    with CTX.Pool(workers) as pool:
        counts = pool.map(estimate_numpy, [per] * workers)
    return assert_pi(pi_from_counts(counts, per * workers))


def measure(workers=WORKERS, total=NUMPY_DARTS):
    """Return {mode: seconds} for numpy serial / threads / processes."""
    return {
        "serial": time_s(lambda: run_serial(total), number=1, repeat=3),
        "threads": time_s(lambda: run_threads(workers, total), number=1, repeat=3),
        "processes": time_s(lambda: run_processes(workers, total), number=1, repeat=3),
    }


def measure_pure_serial(total=TOTAL_DARTS):
    """The pure-Python serial time at ITS native (smaller) dart count.

    We compare numpy vs pure-Python as a per-dart rate, not a raw wall time:
    running pure Python over numpy's 120M darts would take ~half a minute.
    """
    return time_s(lambda: assert_pi(pi_from_counts([estimate_pure(total)], total)),
                  number=1, repeat=1)


def main():
    t = measure()
    print(f"numpy Monte Carlo pi, {NUMPY_DARTS:,} darts, {WORKERS} workers")
    print(f"  serial             : {t['serial']:.3f}s  (1.00x)")
    print(f"  {WORKERS} threads (dummy)  : {t['threads']:.3f}s  "
          f"({t['serial'] / t['threads']:.2f}x)  <- numpy releases the GIL")
    print(f"  {WORKERS} processes       : {t['processes']:.3f}s  "
          f"({t['serial'] / t['processes']:.2f}x)")
    pure = measure_pure_serial()
    numpy_rate = NUMPY_DARTS / t["serial"]            # darts/sec, serial
    pure_rate = TOTAL_DARTS / pure                     # darts/sec, serial
    print(f"  (serial numpy is {numpy_rate / pure_rate:.0f}x faster per dart than "
          f"the pure-Python loop, before any parallelism)")


if __name__ == "__main__":
    main()
