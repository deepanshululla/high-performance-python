"""ex10 — LogLog, HyperLogLog, and K-Minimum-Values: counting uniques in a sketch.

These structures estimate *cardinality* — how many distinct items a stream contained —
without storing the items. The LogLog family exploits a coin-flip insight: the longest
run of leading zeros in the hashes you've seen reveals roughly how many distinct hashes
went by (a run of k zeros happens about once per 2**k items). A single such register is
wildly noisy, so the family splits the hash space across many registers ("flippers") and
combines them — classic LogLog averages them, HyperLogLog uses a harmonic mean with
edge-case corrections, and the error shrinks as ~1.04/sqrt(m) with m registers.
K-Minimum-Values takes a different route: keep the k smallest unique hashes and infer the
count from how tightly they're spaced.

We feed a known number of unique items through each structure and compare estimate,
error, and memory against an exact `set`, then sweep HyperLogLog's register count to show
the error tracking the 1.04/sqrt(m) law — and that a lone LogLog register is hopeless.
"""
import pathlib
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir -> _pds

from _pds import KMinValues, LL, LogLogRegister, HyperLogLog  # noqa: E402

N = 100_000          # true number of unique items
P = 12               # 2**12 = 4096 registers for the head-to-head
K = 1024             # K-Minimum-Values size
P_SWEEP = [4, 6, 8, 10, 12, 14]
TRIALS = 5


def _feed(structure, n, salt=0):
    for i in range(n):
        structure.add(f"{salt}:{i}")     # salt varies the hashes across trials
    return structure


def head_to_head(n=N, p=P, k=K):
    """Estimate n uniques with each structure; report estimate, error, and bytes."""
    rows = []
    llr = _feed(LogLogRegister(), n)
    rows.append(("LogLog register", len(llr), 4))           # ~one 32-bit register
    ll = _feed(LL(p), n)
    rows.append((f"LogLog (p={p})", len(ll), ll.num_bytes()))
    hll = _feed(HyperLogLog(p), n)
    rows.append((f"HyperLogLog (p={p})", len(hll), hll.num_bytes()))
    kmv = _feed(KMinValues(k), n)
    rows.append((f"KMinValues (k={k})", len(kmv), kmv.num_bytes()))
    exact = set(f"0:{i}" for i in range(n))
    rows.append(("set (exact)", len(exact), _set_bytes(exact)))
    return [{"name": nm, "est": est, "bytes": b, "err": (est - n) / n}
            for nm, est, b in rows]


def _set_bytes(s):
    # rough: each str element plus the set's slot; enough to show the orders-of-magnitude gap
    return sum(sys.getsizeof(x) for x in s) + sys.getsizeof(s)


def hll_error_vs_registers(n=N, p_sweep=P_SWEEP, trials=TRIALS):
    """Mean |relative error| of HyperLogLog vs the theoretical 1.04/sqrt(m)."""
    rows = []
    for p in p_sweep:
        m = 2 ** p
        errs = []
        for t in range(trials):
            hll = _feed(HyperLogLog(p), n, salt=t)
            errs.append(abs(len(hll) - n) / n)
        rows.append({"p": p, "registers": m, "bytes": m,
                     "mean_abs_err": statistics.fmean(errs),
                     "theory": 1.04 / (m ** 0.5)})
    return rows


def measure():
    return {"head_to_head": head_to_head(),
            "hll_sweep": hll_error_vs_registers()}


def main():
    m = measure()
    print(f"Estimating {N:,} unique items (exact set shown for scale):\n")
    print(f"  {'structure':22} {'estimate':>12} {'error':>9} {'memory':>12}")
    for r in m["head_to_head"]:
        mem = (f"{r['bytes']/1024/1024:.1f} MiB" if r["bytes"] > 1e6
               else f"{r['bytes']:,} B")
        print(f"  {r['name']:22} {r['est']:12,} {r['err']:+8.1%} {mem:>12}")

    print(f"\nHyperLogLog error vs register count (mean |error| over {TRIALS} trials):")
    print(f"  {'p':>3} {'registers':>10} {'bytes':>8} {'measured':>10} {'1.04/√m':>10}")
    for r in m["hll_sweep"]:
        print(f"  {r['p']:3} {r['registers']:10,} {r['bytes']:8,} "
              f"{r['mean_abs_err']:9.2%} {r['theory']:9.2%}")
    print("\nMeasured error tracks the 1.04/√m law; more registers (more RAM) buys "
          "proportionally less error — capacity is effectively unbounded.")


if __name__ == "__main__":
    main()
