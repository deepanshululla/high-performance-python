"""The Monte Carlo pi workload, shared by ex01-ex04.

Throw darts at the unit square; the fraction landing inside the quarter circle
(x*x + y*y <= 1) approximates pi/4, so 4 * inside / total ~= pi. It is a
deliberately wasteful way to compute pi, but the workload is perfectly even and
embarrassingly parallel, which makes it the ideal lens for watching processes,
threads and the GIL behave.

Two implementations time the *identical* computation:

* `estimate_pure(n)` — a Python `for` loop over `random.uniform`, one float object
  per draw. Slow, and every bytecode is GIL-bound.
* `estimate_numpy(n)` — the same draw vectorised over a `numpy` array. Much of the
  arithmetic runs in C with the GIL released, which (surprisingly) lets *threads*
  help here when they cannot for the pure-Python version.

Correctness anchor: with N >= a few million, 4 * inside / N must land within 0.01
of math.pi. A variant that parallelises by computing the wrong thing fails this.
"""
import math
import random

import numpy as np

# A total dart count large enough that the estimate is stable to ~2 decimals but
# small enough that the pure-Python serial run is a couple of seconds, not a minute.
TOTAL_DARTS = 24_000_000
# numpy is ~20x faster per dart, so it needs a much bigger budget before the
# timings are big enough to read a parallel signal out of the noise.
NUMPY_DARTS = 120_000_000
PI_TOLERANCE = 0.01


def estimate_pure(nbr_estimates):
    """Count darts inside the quarter circle with a pure-Python loop."""
    inside = 0
    for _ in range(int(nbr_estimates)):
        x = random.uniform(0, 1)
        y = random.uniform(0, 1)
        inside += x * x + y * y <= 1.0
    return inside


def estimate_numpy(nbr_estimates):
    """Count darts inside the quarter circle with vectorised numpy.

    np.random.seed() is called per process: every forked child inherits the
    parent's RNG state, so without a fresh seed each worker would draw the
    *same* sequence and the extra workers would add no information.
    """
    np.random.seed()
    n = int(nbr_estimates)
    xs = np.random.uniform(0, 1, n)
    ys = np.random.uniform(0, 1, n)
    return int(np.sum(xs * xs + ys * ys <= 1.0))


def pi_from_counts(counts, total_darts):
    """Combine per-worker inside-counts into a single pi estimate."""
    return sum(counts) * 4 / float(total_darts)


def assert_pi(pi_estimate):
    """Correctness anchor: the estimate must actually approximate pi."""
    assert abs(pi_estimate - math.pi) < PI_TOLERANCE, (
        f"pi estimate {pi_estimate} is not within {PI_TOLERANCE} of math.pi — "
        "the parallel split computed the wrong thing"
    )
    return pi_estimate
