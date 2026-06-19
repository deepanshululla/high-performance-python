"""ex01 — estimating pi on a local IPython Parallel cluster (Examples 11-1..11-5).

This is the book's headline cluster example, run end to end as a script. We start
a local cluster of engines, confirm we can see them, push a function out to all of
them, and use them to estimate pi by Monte Carlo — the same embarrassingly
parallel job from Chapter 10, now farmed out through IPython Parallel's ZeroMQ
machinery instead of a `multiprocessing.Pool`.

The point of the exercise is to make two costs visible and separate:

  * **Startup** — bringing the cluster up (controller + N engine kernels, each
    connecting back over ZeroMQ). This is paid once and is *not* part of the
    compute; the book quietly runs `ipcluster start -n 4` before timing anything.
  * **Compute** — the actual pi estimate once the cluster is warm. This is what
    the book's ~47 s figure measures, and it is what should scale with engines.

We compare the warm cluster compute against a single-process serial baseline
running the identical `estimate_pi_block`, so the speedup is attributable to the
engines and nothing else. A correctness anchor asserts the combined estimate
really approximates pi, so a split that lost or double-counted darts fails loudly.
"""
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root -> perf
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir -> _cluster, _ipp

from _cluster import estimate_pi_block, pi_from_counts, assert_pi  # noqa: E402
from _ipp import local_cluster, prepare_engines                    # noqa: E402

N_ENGINES = 8
DARTS_PER_ENGINE = 10_000_000          # ~1 s of pure-Python work per engine
TOTAL_DARTS = N_ENGINES * DARTS_PER_ENGINE
REPEAT = 3                             # best-of for the warm cluster compute


def measure():
    """Return startup seconds, serial seconds, and best warm cluster seconds."""
    # Serial baseline: one process, the whole dart budget.
    t0 = time.perf_counter()
    serial_counts = [estimate_pi_block(TOTAL_DARTS)]
    serial_s = time.perf_counter() - t0
    assert_pi(pi_from_counts(serial_counts, TOTAL_DARTS))

    with local_cluster(N_ENGINES, return_startup=True) as (rc, startup_s):
        prepare_engines(rc)
        dview = rc[:]
        assert len(rc.ids) == N_ENGINES, f"expected {N_ENGINES} engines, saw {rc.ids}"

        best = None
        for _ in range(REPEAT):
            t0 = time.perf_counter()
            counts = dview.apply_sync(estimate_pi_block, DARTS_PER_ENGINE)
            dt = time.perf_counter() - t0
            assert_pi(pi_from_counts(counts, TOTAL_DARTS))
            best = dt if best is None else min(best, dt)

    return {"startup": startup_s, "serial": serial_s, "cluster": best}


def main():
    r = measure()
    speedup = r["serial"] / r["cluster"]
    print(f"Monte Carlo pi, {TOTAL_DARTS:,} darts, {N_ENGINES} IPython engines")
    print(f"  cluster startup : {r['startup']:6.2f} s  (paid once, not compute)")
    print(f"  serial (1 proc) : {r['serial']:6.2f} s")
    print(f"  cluster (warm)  : {r['cluster']:6.2f} s   -> {speedup:.2f}x speedup")
    print(f"  startup is {r['startup'] / r['cluster']:.1f}x the compute it accelerates — "
          "the cluster only pays off when the job dwarfs it")


if __name__ == "__main__":
    main()
