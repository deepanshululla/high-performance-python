"""The prime-checking workload, shared by ex05-ex07.

Unlike the Monte Carlo pi job, primality testing has *unpredictable* per-item
cost: an even number is rejected in one step, a large prime forces a trial of
every odd factor up to sqrt(n). That uneven cost is exactly what makes prime
work the right vehicle for studying chunking (ex05), queue overhead (ex06) and
interprocess early-exit flags (ex07).

`check_prime` is the trial-division test from the book. `check_prime_in_range`
checks only a slice of the factor space [from_i, to_i), so a single large number
can be split across CPUs. `create_range` cuts [from_i, to_i) into N contiguous
slices, each starting on an odd number (the inner loop steps by 2).

The five validation numbers are the book's: a small nonprime, two 18-digit
nonprimes and two 18-digit primes. The nonprimes have *large* smallest-factors,
so a serial sweep is slow and parallel search can win; the primes have no factor
at all, so nothing can exit early — the worst case for any early-exit scheme.
"""
import math

# Book's validation set (Chapter 10, "Verifying Primes Using IPC").
SMALL_NONPRIME = 112_272_535_095_295
LARGE_NONPRIME_1 = 100_109_100_129_100_369
LARGE_NONPRIME_2 = 100_109_100_129_101_027
PRIME_1 = 100_109_100_129_100_151
PRIME_2 = 100_109_100_129_162_907

VALIDATION_NUMBERS = [
    ("small nonprime", SMALL_NONPRIME, False),
    ("large nonprime 1", LARGE_NONPRIME_1, False),
    ("large nonprime 2", LARGE_NONPRIME_2, False),
    ("prime 1", PRIME_1, True),
    ("prime 2", PRIME_2, True),
]


def check_prime(n):
    """Serial trial division; the book's baseline (exits early on even n)."""
    if n % 2 == 0:
        return False
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        if n % i == 0:
            return False
    return True


def check_prime_in_range(n_from_i_to_i):
    """Check whether n has a factor in the odd range [from_i, to_i).

    Returns False as soon as a factor is found (n is not prime), else True
    meaning 'no factor in *this* slice'. Packed as one argument so it drops
    straight into pool.map.
    """
    (n, (from_i, to_i)) = n_from_i_to_i
    if n % 2 == 0:
        return False
    assert from_i % 2 != 0
    for i in range(from_i, int(to_i), 2):
        if n % i == 0:
            return False
    return True


def create_range(from_i, to_i, nbr_pieces):
    """Split [from_i, to_i) into nbr_pieces contiguous slices that start odd."""
    step = (to_i - from_i) // nbr_pieces
    ranges = []
    lower = from_i
    for i in range(nbr_pieces):
        upper = lower + step
        if i == nbr_pieces - 1:
            upper = to_i
        if lower % 2 == 0:          # the inner loop steps by 2 from an odd start
            lower += 1
        ranges.append((lower, upper))
        lower = upper
    return ranges
