"""ex01 — the same pure-Python pi job, run three ways: serial, threads, processes.

This is the chapter's opening lesson and the cleanest demonstration of the GIL.
We hand an *identical*, evenly-divisible Monte Carlo workload to:

* one process, one loop (serial);
* a pool of threads (multiprocessing.dummy wraps threading);
* a pool of forked processes (multiprocessing).

Threads should give essentially no speedup — every dart draw is pure-Python
bytecode, so the GIL lets only one thread make progress at a time. Processes
should scale, because each forked interpreter has its own GIL and runs flat out
on its own core. We split the dart budget evenly so each worker does the same
amount of work and the comparison is fair.
"""
import pathlib
import sys
from multiprocessing.dummy import Pool as ThreadPool

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root -> perf
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir -> _pi, _mp

from perf import time_s  # noqa: E402
from _pi import estimate_pure, pi_from_counts, assert_pi, TOTAL_DARTS  # noqa: E402
from _mp import CTX  # noqa: E402

WORKERS = 4   # the comparison point: 4 threads vs 4 processes vs 1 serial loop


def run_serial(total=TOTAL_DARTS):
    return assert_pi(pi_from_counts([estimate_pure(total)], total))


def run_threads(workers=WORKERS, total=TOTAL_DARTS):
    per = total // workers
    with ThreadPool(workers) as pool:
        counts = pool.map(estimate_pure, [per] * workers)
    return assert_pi(pi_from_counts(counts, per * workers))


def run_processes(workers=WORKERS, total=TOTAL_DARTS):
    per = total // workers
    with CTX.Pool(workers) as pool:
        counts = pool.map(estimate_pure, [per] * workers)
    return assert_pi(pi_from_counts(counts, per * workers))


def measure(workers=WORKERS, total=TOTAL_DARTS):
    """Return {mode: seconds} for serial / threads / processes (one run each)."""
    return {
        "serial": time_s(lambda: run_serial(total), number=1, repeat=1),
        "threads": time_s(lambda: run_threads(workers, total), number=1, repeat=1),
        "processes": time_s(lambda: run_processes(workers, total), number=1, repeat=1),
    }


def main():
    t = measure()
    print(f"pure-Python Monte Carlo pi, {TOTAL_DARTS:,} darts, {WORKERS} workers")
    print(f"  serial            : {t['serial']:.2f}s  (1.00x)")
    print(f"  {WORKERS} threads (dummy) : {t['threads']:.2f}s  "
          f"({t['serial'] / t['threads']:.2f}x)  <- GIL: no speedup")
    print(f"  {WORKERS} processes      : {t['processes']:.2f}s  "
          f"({t['serial'] / t['processes']:.2f}x)  <- one GIL per process")


if __name__ == "__main__":
    main()
