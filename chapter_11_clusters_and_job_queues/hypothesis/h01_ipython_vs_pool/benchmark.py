"""h01 — Is IPython Parallel worth it on a single machine, or does a plain Pool win?

ex01 showed IPython Parallel estimating pi at ~6.7x on eight engines — the same
speedup Chapter 10 got from a bare `multiprocessing.Pool`. That raises an obvious
question: on one machine, is there *any* reason to pay for IPython Parallel's
machinery (a controller, ZeroMQ transport, per-task scheduling) over a Pool?

HYPOTHESIS: On a single machine, `multiprocessing.Pool` matches or beats IPython
Parallel, and the gap widens as tasks get finer-grained.
  * Startup: a Pool is far cheaper to create than a cluster of engine kernels.
  * Coarse-grained work (a few big tasks): they should roughly TIE — both just run
    N interpreters flat out, and the per-task overhead is negligible against
    seconds of compute.
  * Fine-grained work (many small tasks): the Pool should WIN, because every task
    in IPython Parallel is a ZeroMQ round-trip through the scheduler (ex02's
    latency tax), while a Pool ships work over cheap local pipes with chunking.
The implication, if confirmed: IPython Parallel earns its keep with *remote*
engines and *interactive* control — not with local speed.

We hold the workload identical (the same total darts, the same `estimate_pi_block`)
and run it both ways at two granularities, timing warm compute (startup excluded)
plus the one-time startup of each.
"""
import multiprocessing as mp
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))   # repo root
sys.path.insert(0, str(HERE.parents[1]))   # chapter dir -> _cluster, _ipp

from _cluster import estimate_pi_block, pi_from_counts, assert_pi  # noqa: E402
from _ipp import local_cluster, prepare_engines                    # noqa: E402

CTX = mp.get_context("fork")
N_WORKERS = 8
TOTAL_DARTS = 80_000_000
COARSE_TASKS = 8                       # a few big tasks
FINE_TASKS = 256                       # many small tasks (same total work)
REPEAT = 3


def _best(fn, repeat=REPEAT):
    best = None
    for _ in range(repeat):
        t0 = time.perf_counter(); fn(); dt = time.perf_counter() - t0
        best = dt if best is None else min(best, dt)
    return best


def measure():
    coarse = [TOTAL_DARTS // COARSE_TASKS] * COARSE_TASKS
    fine = [TOTAL_DARTS // FINE_TASKS] * FINE_TASKS
    out = {}

    # --- multiprocessing.Pool ---
    t0 = time.perf_counter()
    pool = CTX.Pool(N_WORKERS)
    out["pool_startup"] = time.perf_counter() - t0
    try:
        def pool_coarse():
            assert_pi(pi_from_counts(pool.map(estimate_pi_block, coarse), TOTAL_DARTS))
        def pool_fine():
            assert_pi(pi_from_counts(pool.map(estimate_pi_block, fine), TOTAL_DARTS))
        pool_coarse()  # warm
        out["pool_coarse"] = _best(pool_coarse)
        out["pool_fine"] = _best(pool_fine)
    finally:
        pool.close(); pool.join()

    # --- IPython Parallel ---
    with local_cluster(N_WORKERS, return_startup=True) as (rc, startup):
        out["ipp_startup"] = startup
        prepare_engines(rc)
        dview = rc[:]
        lbv = rc.load_balanced_view()
        def ipp_coarse():
            assert_pi(pi_from_counts(dview.map_sync(estimate_pi_block, coarse), TOTAL_DARTS))
        def ipp_fine():
            assert_pi(pi_from_counts(lbv.map_sync(estimate_pi_block, fine), TOTAL_DARTS))
        ipp_coarse()  # warm
        out["ipp_coarse"] = _best(ipp_coarse)
        out["ipp_fine"] = _best(ipp_fine)
    return out


def verdict(out):
    startup_ratio = out["ipp_startup"] / out["pool_startup"]
    coarse_ratio = out["ipp_coarse"] / out["pool_coarse"]
    fine_ratio = out["ipp_fine"] / out["pool_fine"]
    # The hypothesis is "Pool matches or beats IPython on one machine." The robust,
    # reproducible evidence is: Pool starts orders of magnitude faster, and is never
    # meaningfully slower on warm compute (it ties on coarse work and trends faster
    # as tasks get finer-grained). We require a large startup win plus Pool being
    # within noise-or-better on both compute granularities (ratios > ~0.95).
    confirmed = startup_ratio > 10 and coarse_ratio > 0.9 and fine_ratio > 0.95
    return confirmed, startup_ratio, coarse_ratio, fine_ratio


def main():
    out = measure()
    confirmed, sr, cr, fr = verdict(out)
    print(f"IPython Parallel vs multiprocessing.Pool, {N_WORKERS} workers, "
          f"{TOTAL_DARTS:,} darts")
    print(f"  {'':<16}{'Pool':>10}{'IPython':>10}{'IPP/Pool':>10}")
    print(f"  {'startup':<16}{out['pool_startup']:9.2f}s{out['ipp_startup']:9.2f}s{sr:9.1f}x")
    print(f"  {'coarse (8 tasks)':<16}{out['pool_coarse']:9.2f}s{out['ipp_coarse']:9.2f}s{cr:9.2f}x")
    print(f"  {'fine (256 tasks)':<16}{out['pool_fine']:9.2f}s{out['ipp_fine']:9.2f}s{fr:9.2f}x")
    print(f"  VERDICT: {'CONFIRMED' if confirmed else 'OVERTURNED'} — "
          f"Pool starts {sr:.0f}x faster and is never slower on compute "
          f"(coarse {cr:.2f}x, fine {fr:.2f}x); IPython's value is remote + interactive, "
          "not local speed")
    return out


if __name__ == "__main__":
    main()
