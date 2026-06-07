"""Chapter 6 - Exercise 1: norm-squared, pure Python vs numpy (Examples ~6 "Enter numpy").

Task: compute sum(v*v) four ways -- explicit Python loop, list comprehension,
numpy `vector * vector` then `sum`, and the specialized `numpy.dot` -- and
compare time + memory.

Takeaway: the win is "code you don't run." numpy issues a fraction of the
instructions because it calls specialized C over a contiguous, homogeneous,
typed buffer -- no per-element type checks, no pointer-chasing. `dot` wins
again by fusing multiply+sum into one pass with no temporary array.

Run: .venv/bin/python chapter_6/ex01_list_vs_numpy_norm.py
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from perf import peak_bytes, time_s, human  # noqa: E402


def norm_square_list(vector):
    norm = 0
    for v in vector:
        norm += v * v
    return norm


def norm_square_list_comprehension(vector):
    return sum([v * v for v in vector])


def norm_square_numpy(vector):
    return np.sum(vector * vector)        # two implied loops: multiply, then sum


def norm_square_numpy_dot(vector):
    return np.dot(vector, vector)         # one fused pass, no temporary array


def main():
    N = 1_000_000
    py = list(range(N))
    npv = np.arange(N)

    # Correctness: all four agree.
    expected = norm_square_list(py)
    assert norm_square_list_comprehension(py) == expected
    assert int(norm_square_numpy(npv)) == expected
    assert int(norm_square_numpy_dot(npv)) == expected
    print(f"All four agree on sum(v*v) for range({N:,}) = {expected}")

    cases = [
        ("python loop      ", lambda: norm_square_list(py)),
        ("list comprehension", lambda: norm_square_list_comprehension(py)),
        ("numpy v*v + sum   ", lambda: norm_square_numpy(npv)),
        ("numpy.dot         ", lambda: norm_square_numpy_dot(npv)),
    ]
    print(f"\nNorm-squared over {N:,} elements:")
    base = None
    for label, fn in cases:
        t = time_s(fn, number=3, repeat=5)
        if base is None:
            base = t
        print(f"  {label}: {t * 1e3:7.2f} ms   ({base / t:5.1f}x vs python loop)   peak {human(peak_bytes(fn))}")
    print("  -> numpy runs far fewer instructions over a contiguous typed buffer;")
    print("     dot fuses multiply+sum so it never materializes v*v.")


if __name__ == "__main__":
    main()
