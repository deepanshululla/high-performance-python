"""Chapter 3 - Exercise 4: find the closest value with bisect.

Task: given a sorted list, return the index of the element nearest to `needle`.
Handle below-min, above-max, and tie-to-lower. Use bisect.insort to keep the
list sorted as it is built (so it never needs re-sorting).

Run: .venv/bin/python chapter_3/ex04_find_closest.py
"""
import bisect
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from perf import time_s  # noqa: E402


def find_closest(haystack, needle):
    # bisect_left returns the first index whose value is >= needle.
    i = bisect.bisect_left(haystack, needle)
    if i == len(haystack):          # needle is above everything
        return i - 1
    if haystack[i] == needle:
        return i
    if i > 0:                       # compare with the left neighbour
        j = i - 1
        if haystack[i] - needle > needle - haystack[j]:
            return j
    return i


def main():
    random.seed(1)
    nums = []
    for _ in range(10):
        bisect.insort(nums, random.randint(0, 1000))  # stays sorted on insert
    print("sorted via insort:", nums)
    for q in (-250, 500, 1100):
        idx = find_closest(nums, q)
        print(f"closest to {q:>5}: {nums[idx]} (index {idx})")

    # Time analysis: keeping sorted (insort, O(n)) vs searching (find_closest, O(log n)).
    big = sorted(random.randint(0, 10_000_000) for _ in range(1_000_000))
    t_insort = time_s(lambda: bisect.insort(big, 5_000_000), number=100)
    t_search = time_s(lambda: find_closest(big, 5_000_000), number=10_000)
    print("\nTime (1,000,000-element sorted list):")
    print(f"  insort (keep sorted): {t_insort * 1e6:8.2f} us  (O(n): shifts elements)")
    print(f"  find_closest (search):{t_search * 1e6:8.2f} us  (O(log n): ~20 probes)")
    print("Memory: O(1) auxiliary; insort mutates in place, search allocates nothing.")


if __name__ == "__main__":
    main()
