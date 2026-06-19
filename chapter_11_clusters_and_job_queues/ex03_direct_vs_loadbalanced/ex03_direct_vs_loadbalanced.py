"""ex03 — direct view vs load-balanced view: who keeps the engines busy?

IPython Parallel gives you two ways to hand work to engines, and the book names
both. A **direct view** (`rc[:]`) addresses the engines directly: its `map`
splits the work into one contiguous chunk per engine and ships each chunk off in
a single message — a *static* assignment decided up front. A **load-balanced
view** (`rc.load_balanced_view()`) goes through a scheduler that hands out one
task at a time to whichever engine is next free — a *dynamic* assignment decided
as the work runs.

On perfectly even work the two are indistinguishable. The difference appears the
moment the work is *uneven*, which real work always is. We build a lopsided list
of dart-counting blocks — most small, a random handful many times larger — and
run the identical blocks through both views. The static split is hostage to
whichever engine drew the heavy blocks: it finishes only when its straggler does,
while the engines that drew light chunks sit idle. The scheduler keeps every
engine fed until the work runs out.

This is the cluster-scale echo of Chapter 10's `chunksize` exercise: the same
tension between paying scheduling overhead and leaving cores idle, one level up.
"""
import collections
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[0]))

from _cluster import (pi_block_with_pid, pi_from_counts, assert_pi,  # noqa: E402
                      uneven_blocks)
from _ipp import local_cluster, prepare_engines  # noqa: E402

N_ENGINES = 8
N_BLOCKS = 48
BASE_DARTS = 1_000_000
SPREAD = 12                # heaviest blocks are up to ~12x the base
REPEAT = 2


def _per_engine_darts(blocks, results):
    """Sum the darts each engine (by pid) actually processed."""
    load = collections.defaultdict(int)
    for n, (pid, _inside) in zip(blocks, results):
        load[pid] += n
    return dict(load)


def measure():
    blocks = uneven_blocks(N_BLOCKS, BASE_DARTS, SPREAD)
    total = sum(blocks)
    out: dict = {"total_darts": total, "n_blocks": N_BLOCKS}

    with local_cluster(N_ENGINES) as rc:
        prepare_engines(rc)
        dview = rc[:]
        lbv = rc.load_balanced_view()

        def run(view):
            results = view.map_sync(pi_block_with_pid, blocks)
            counts = [inside for _pid, inside in results]
            assert_pi(pi_from_counts(counts, total))
            return results

        # warm both code paths once, then time best-of-REPEAT
        direct_best = lb_best = None
        direct_results = lb_results = None
        for _ in range(REPEAT):
            t0 = time.perf_counter(); direct_results = run(dview)
            dt = time.perf_counter() - t0
            direct_best = dt if direct_best is None else min(direct_best, dt)
            t0 = time.perf_counter(); lb_results = run(lbv)
            dt = time.perf_counter() - t0
            lb_best = dt if lb_best is None else min(lb_best, dt)

        out["direct_s"] = direct_best
        out["lb_s"] = lb_best
        out["direct_load"] = _per_engine_darts(blocks, direct_results)
        out["lb_load"] = _per_engine_darts(blocks, lb_results)
    return out


def main():
    r = measure()
    sp = r["direct_s"] / r["lb_s"]
    dl = sorted(r["direct_load"].values())
    ll = sorted(r["lb_load"].values())
    imb = lambda v: max(v) / min(v)  # noqa: E731
    print(f"uneven workload: {r['n_blocks']} blocks, {r['total_darts']:,} darts total, "
          f"{N_ENGINES} engines")
    print(f"  direct view  (static split)  : {r['direct_s']:5.2f} s   "
          f"per-engine darts {min(dl)/1e6:.0f}-{max(dl)/1e6:.0f}M (imbalance {imb(dl):.1f}x)")
    print(f"  load-balanced (on-demand)    : {r['lb_s']:5.2f} s   "
          f"per-engine darts {min(ll)/1e6:.0f}-{max(ll)/1e6:.0f}M (imbalance {imb(ll):.1f}x)")
    print(f"  load balancing is {sp:.2f}x faster — the static split waits on its straggler")


if __name__ == "__main__":
    main()
