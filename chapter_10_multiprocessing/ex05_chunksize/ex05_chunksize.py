"""ex05 — chunksize: the dial between communication overhead and idle CPUs.

When `Pool.map` hands work out, `chunksize` sets how many items travel through
the IPC pipe per message. Too small and every item is its own pickled round-trip,
so the single pipe becomes the bottleneck and the CPUs starve waiting for work.
Too large and the items don't divide evenly across workers, so the last few
chunks run alone while most cores sit idle. The sweet spot — which is roughly
what `multiprocessing` picks by default — is many small chunks, but not *one per
item*.

We test primality across 100,000 consecutive numbers near 10^9 (each check trials
odd factors up to ~31,623, so the per-item work is real, not trivial) and sweep
`chunksize` from 1 to 50,000, plus the library default.

A second view sweeps the *number of chunks* instead, which exposes the sawtooth:
runtime dips whenever the chunk count is a multiple of the worker count (work
divides evenly) and spikes just after (one straggler chunk runs alone).
"""
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[0]))

from perf import time_s  # noqa: E402
from _primes import check_prime  # noqa: E402
from _mp import CTX  # noqa: E402

WORKERS = 8
LO, HI = 1_000_000_000, 1_000_100_000        # 100,000 numbers
NUMBERS = list(range(LO, HI))
EXPECTED_PRIMES = 4832                         # correctness anchor (verified once)
CHUNKSIZES = [1, 2, 8, 64, 256, 1024, 4096, 50000]


def _run(chunksize=None, workers=WORKERS):
    with CTX.Pool(workers) as pool:
        if chunksize is None:
            results = pool.map(check_prime, NUMBERS)
        else:
            results = pool.map(check_prime, NUMBERS, chunksize=chunksize)
    primes = sum(results)
    assert primes == EXPECTED_PRIMES, f"got {primes} primes, expected {EXPECTED_PRIMES}"
    return primes


def measure_serial():
    def once():
        primes = sum(check_prime(n) for n in NUMBERS)
        assert primes == EXPECTED_PRIMES
    return time_s(once, number=1, repeat=1)


def sweep_chunksize(chunksizes=CHUNKSIZES, workers=WORKERS):
    """Return ([(chunksize, seconds)...], default_seconds)."""
    rows = [(cs, time_s(lambda cs=cs: _run(cs, workers), number=1, repeat=1))
            for cs in chunksizes]
    default = time_s(lambda: _run(None, workers), number=1, repeat=1)
    return rows, default


def sweep_chunkcount(counts=range(1, 21), workers=WORKERS):
    """Return [(nbr_chunks, seconds)...] — the sawtooth view."""
    rows = []
    for nbr in counts:
        cs = max(1, math.ceil(len(NUMBERS) / nbr))
        rows.append((nbr, time_s(lambda cs=cs: _run(cs, workers), number=1, repeat=1)))
    return rows


def main():
    serial = measure_serial()
    rows, default = sweep_chunksize()
    print(f"prime sieve over {len(NUMBERS):,} numbers, {WORKERS} workers")
    print(f"  serial               : {serial:.2f}s  (1.00x)")
    for cs, t in rows:
        nchunks = math.ceil(len(NUMBERS) / cs)
        print(f"  chunksize {cs:>6} ({nchunks:>6} chunks): {t:.3f}s  "
              f"speedup {serial / t:.2f}x")
    print(f"  chunksize default     : {default:.3f}s  speedup {serial / default:.2f}x")


if __name__ == "__main__":
    main()
