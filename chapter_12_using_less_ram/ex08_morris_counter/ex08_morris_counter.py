"""ex08 — the Morris counter: counting to billions in a single byte.

The Morris counter (Robert Morris, NSA / Bell Labs) is the simplest probabilistic
counter. Instead of storing the count, it stores an *exponent* and represents the
count as 2**exponent. To increment, it doesn't always tick: when the current value is
2**k, it increments the exponent only with probability 1/2**k. So early increments
almost always fire, later ones rarely do, and the exponent climbs roughly as
log2(count). One unsigned byte holds an exponent up to 255, which represents a count up
to 2**255 ≈ 5e76 — where an exact 8-byte integer tops out at ~1.8e19.

The price is accuracy: the estimate is noisy, and because it's a single random walk,
one lucky early increment can throw a counter off for a long time. We reproduce the
increment-probability table, watch several independent counters track a true count, and
measure how the relative error behaves as the count grows over many trials.
"""
import pathlib
import random
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir -> _pds

from _pds import MorrisCounter  # noqa: E402

N = 100_000          # iterations for the trajectory plot
N_TRAJECTORIES = 6   # independent counters to overlay
TRIALS = 200         # independent counters per error-sweep point
ERROR_COUNTS = [1_000, 10_000, 100_000]


def probability_table(max_exponent=6):
    """Reproduce Table 12-1: P(increment) = 1/2**exponent for the first exponents."""
    return [(e, 2 ** e, 1.0 / 2 ** e) for e in range(max_exponent)]


def trajectories(n=N, k=N_TRAJECTORIES, seed=0):
    """Run k independent counters to n adds; sample (iteration, estimate) log-spaced."""
    random.seed(seed)
    counters = [MorrisCounter() for _ in range(k)]
    # log-spaced sample points so the early fast climb and late plateau both show.
    sample_at = sorted({int(round(10 ** (5 * i / 60))) for i in range(61)})  # 1..1e5
    sample_at = [s for s in sample_at if 1 <= s <= n]
    samples = {i: [] for i in range(k)}
    iters = []
    nxt = set(sample_at)
    for it in range(1, n + 1):
        for c in counters:
            c.add()
        if it in nxt:
            iters.append(it)
            for i, c in enumerate(counters):
                samples[i].append(c.get())
    return iters, samples


def error_sweep(counts=ERROR_COUNTS, trials=TRIALS, seed=1):
    """For each true count, run many counters and report mean estimate + relative error."""
    random.seed(seed)
    rows = []
    for true in counts:
        ests = []
        for _ in range(trials):
            c = MorrisCounter()
            for _ in range(true):
                c.add()
            ests.append(c.get())
        mean = statistics.fmean(ests)
        stdev = statistics.pstdev(ests)
        rows.append({"true": true, "mean_est": mean, "stdev": stdev,
                     "rel_err": stdev / true, "bias": (mean - true) / true})
    return rows


def measure():
    iters, samples = trajectories()
    return {
        "table": probability_table(),
        "iters": iters,
        "samples": samples,
        "error": error_sweep(),
    }


def main():
    print("Table 12-1 — Morris increment probabilities:")
    print(f"  {'exponent':>8} {'2**exp':>14} {'P(increment)':>14}")
    for e, val, p in probability_table():
        print(f"  {e:8} {val:14,} {p:14.5f}")

    print(f"\nByte budget: 1-byte exponent counts to 2**255 ≈ {2.0**255:.1e}; "
          f"an 8-byte int tops out at {2**63 - 1:,}.")

    print(f"\nError sweep ({TRIALS} independent counters per count):")
    print(f"  {'true':>8} {'mean est':>12} {'rel error':>10} {'bias':>8}")
    for r in measure()["error"]:
        print(f"  {r['true']:8,} {r['mean_est']:12,.0f} {r['rel_err']:9.1%} "
              f"{r['bias']:+8.1%}")
    print("\nRelative error stays roughly constant as the count grows — the counter "
          "trades a fixed ~percentage accuracy for counting in a single byte.")


if __name__ == "__main__":
    main()
