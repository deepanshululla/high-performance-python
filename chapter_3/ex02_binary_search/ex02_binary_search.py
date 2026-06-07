"""Chapter 3 - Exercise 2: binary search vs linear search (list.index).

Task: implement binary_search(needle, haystack) for a *sorted* list, returning
the index or -1. Prove it matches list.index across many random queries.

Takeaway: with known order, search collapses from O(n) (list.index / linear
scan) to O(log n) -- each comparison discards half the remaining range.

Run: .venv/bin/python chapter_3/ex02_binary_search/ex02_binary_search.py
"""
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from perf import time_s  # noqa: E402


def linear_search(needle, array):
    """O(n) -- exactly what list.index() does under the hood."""
    for i, item in enumerate(array):
        if item == needle:
            return i
    return -1


def binary_search(needle, haystack):
    """O(log n) on a sorted list."""
    imin, imax = 0, len(haystack)
    while imin < imax:
        midpoint = (imin + imax) // 2
        if haystack[midpoint] > needle:
            imax = midpoint
        elif haystack[midpoint] < needle:
            imin = midpoint + 1
        else:
            return midpoint
    return -1


def main():
    random.seed(0)
    data = sorted(random.sample(range(1_000_000), 10_000))  # unique + sorted
    for _ in range(20_000):
        if random.random() < 0.5:
            needle = random.choice(data)            # present
        else:
            needle = random.randint(-5, 1_000_005)  # maybe absent
        expected = data.index(needle) if needle in data else -1
        assert binary_search(needle, data) == expected, needle
    print("binary_search matches list.index on 20,000 random queries -- ok")

    # Trace the book's example: find 61 in a small sorted list.
    demo = [9, 18, 18, 19, 29, 42, 56, 61, 88, 95]
    print(f"index of 61 in {demo} -> {binary_search(61, demo)} (expected 7)")

    # Time/memory analysis: worst case = searching for an absent value.
    big = list(range(1_000_000))
    miss = -1
    t_lin = time_s(lambda: linear_search(miss, big), number=10)
    t_bin = time_s(lambda: binary_search(miss, big), number=1000)
    print("\nTime (1,000,000 elements, worst-case miss):")
    print(f"  linear_search: {t_lin * 1e6:9.2f} us  (O(n), scans all)")
    print(f"  binary_search: {t_bin * 1e6:9.2f} us  (O(log n), ~20 probes)")
    print(f"  -> binary search is {t_lin / t_bin:,.0f}x faster")
    print("Memory: both O(1) auxiliary (no copies); the win is purely fewer comparisons.")


if __name__ == "__main__":
    main()
