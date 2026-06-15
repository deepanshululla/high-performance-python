"""ex04 — Joblib: the same parallel pi, with less ceremony and a disk cache.

Joblib wraps the multiprocessing machinery behind `Parallel(n_jobs=...)` and a
`delayed(fn)(args)` iterator. It uses the Loky backend (a hardened process pool)
and cloudpickle, so it sidesteps some of the pickling limits of the raw module.
For an embarrassingly parallel loop the result is the same speedup as ex01's
hand-rolled `Pool`, with a one-liner instead of pool setup.

The second half is the interesting trap. Joblib's `Memory` decorator caches a
function's return *by its arguments* to disk, persisting across runs. For Monte
Carlo that is a footgun: every worker calls `estimate(per_worker)` with the
*same* argument, so a naive cache would store one result and hand back that same
count to all eight workers — collapsing eight independent samples into one and
quietly breaking the estimate. The fix is the book's: pass a distinct `idx` so
each call has a unique signature. Then the first run pays full price and every
later run returns instantly with the *identical* pi.
"""
import pathlib
import shutil
import sys

from joblib import Memory, Parallel, delayed

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[0]))

from perf import time_s  # noqa: E402
from _pi import estimate_pure, pi_from_counts, assert_pi, TOTAL_DARTS  # noqa: E402

WORKERS = 8
CACHE_DIR = HERE / ".joblib_cache"
memory = Memory(str(CACHE_DIR), verbose=0)


@memory.cache
def estimate_with_idx(nbr_estimates, idx):
    """Same estimator, but idx makes each worker's call signature unique so the
    disk cache stores eight distinct counts instead of collapsing them to one."""
    return estimate_pure(nbr_estimates)


def run_joblib(workers=WORKERS, total=TOTAL_DARTS):
    """Plain Joblib parallel run (no caching) — the ex01 Pool, one line."""
    per = total // workers
    counts = Parallel(n_jobs=workers)(
        delayed(estimate_pure)(per) for _ in range(workers)
    )
    return assert_pi(pi_from_counts(counts, per * workers))


def run_cached(workers=WORKERS, total=TOTAL_DARTS):
    """Joblib parallel run whose per-worker results are cached to disk by idx."""
    per = total // workers
    counts = Parallel(n_jobs=workers)(
        delayed(estimate_with_idx)(per, idx) for idx in range(workers)
    )
    return assert_pi(pi_from_counts(counts, per * workers))


def measure(workers=WORKERS, total=TOTAL_DARTS):
    """Return parallel time and the cold/warm cache times + the cached pi."""
    parallel_t = time_s(lambda: run_joblib(workers, total), number=1, repeat=1)
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)        # force a cold cache for an honest measurement
    pi_holder = {}

    def cold():
        pi_holder["pi"] = run_cached(workers, total)
    cold_t = time_s(cold, number=1, repeat=1)
    warm_t = time_s(lambda: run_cached(workers, total), number=1, repeat=1)
    return {
        "parallel": parallel_t,
        "cold": cold_t,
        "warm": warm_t,
        "pi": pi_holder["pi"],
    }


def main():
    m = measure()
    print(f"Joblib Monte Carlo pi, {TOTAL_DARTS:,} darts, {WORKERS} workers")
    print(f"  Parallel/delayed       : {m['parallel']:.2f}s  (same as a hand-rolled Pool)")
    print(f"  Memory cache, cold run : {m['cold']:.2f}s  (computes + writes to disk)")
    print(f"  Memory cache, warm run : {m['warm']:.3f}s  "
          f"({m['cold'] / m['warm']:.0f}x faster, identical pi={m['pi']:.5f})")


if __name__ == "__main__":
    main()
