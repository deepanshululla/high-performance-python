"""ex04 — branchless vector masks: logical AND as x, OR as max, NOT as 1-x.

David Rawlinson notes that many optimisations make code harder to read and verify, and
gives a concrete one: you can implement a *non-forking* logical AND with element-wise
multiplication, OR with `max(a, b)`, and NOT with `1 - x`. "This is less readable but much
faster on floating-point vector or tensor data using many modern libraries." The deeper
point is about *forking* — a per-element `if` branches, and branches are the enemy of
vectorised hardware (SIMD lanes, GPU warps).

We test a compound predicate three ways and time each on identical data:

    result = a  where  (a > 0.5 AND b < 0.5) OR (c > 0.8),  else 0.0

  1. python_loop      — an explicit per-element `if`, the readable, forking baseline.
  2. numpy_boolean    — numpy boolean masks combined with `&`, `|`, `~` (the idiomatic way).
  3. numpy_branchless — float masks (`(a > 0.5).astype(float)`) combined with `*`,
                        `np.maximum`, and `1 -`, then multiplied through. No booleans.

All three must produce the identical result (the anchor). The interesting comparison is
two-layered: vectorising over the Python loop is the order-of-magnitude win, while the
boolean-vs-branchless choice is the subtle one the chapter is really about.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root -> perf

import numpy as np  # noqa: E402

from perf import time_s  # noqa: E402

N = 2_000_000


def _inputs(n=N, seed=0):
    rng = np.random.default_rng(seed)
    return rng.random(n), rng.random(n), rng.random(n)


def predicate_python(a, b, c):
    """Readable, forking: one branch per element in pure Python."""
    out = [0.0] * len(a)
    for i in range(len(a)):
        if (a[i] > 0.5 and b[i] < 0.5) or (c[i] > 0.8):
            out[i] = a[i]
    return np.asarray(out)


def predicate_boolean(a, b, c):
    """Idiomatic numpy: boolean masks combined with &, |, ~."""
    mask = ((a > 0.5) & (b < 0.5)) | (c > 0.8)
    return np.where(mask, a, 0.0)


def predicate_branchless(a, b, c):
    """Branchless float arithmetic: AND = *, OR = max, NOT = 1 - x. No booleans, no where."""
    m_a = (a > 0.5).astype(np.float64)
    m_b = (b < 0.5).astype(np.float64)
    m_c = (c > 0.8).astype(np.float64)
    and_ab = m_a * m_b                       # logical AND
    mask = np.maximum(and_ab, m_c)           # logical OR
    return a * mask                          # select without branching


def measure(n=N, seed=0):
    a, b, c = _inputs(n, seed)
    ref = predicate_python(a, b, c)
    bo = predicate_boolean(a, b, c)
    bl = predicate_branchless(a, b, c)
    assert np.array_equal(ref, bo) and np.array_equal(ref, bl), "paths disagree!"

    # The Python loop is ~6 orders slower; time it once, the numpy paths best-of-5.
    t_py = time_s(lambda: predicate_python(a, b, c), number=1, repeat=2)
    t_bo = time_s(lambda: predicate_boolean(a, b, c), number=1, repeat=5)
    t_bl = time_s(lambda: predicate_branchless(a, b, c), number=1, repeat=5)
    return {
        "n": n,
        "python_loop": t_py, "numpy_boolean": t_bo, "numpy_branchless": t_bl,
        "vectorize_speedup": t_py / t_bo,
        "branchless_vs_boolean": t_bo / t_bl,
    }


def main():
    m = measure()
    print(f"compound predicate over {m['n']:,} floats:\n")
    for name in ("python_loop", "numpy_boolean", "numpy_branchless"):
        print(f"  {name:18}: {m[name]*1e3:9.2f} ms")
    print(f"\n  vectorising (loop -> numpy):   {m['vectorize_speedup']:8.0f}x")
    print(f"  branchless vs boolean masks:   {m['branchless_vs_boolean']:8.2f}x")


if __name__ == "__main__":
    main()
