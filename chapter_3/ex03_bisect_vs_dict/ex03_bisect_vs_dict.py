"""Chapter 3 - Exercise 3: sorted-list + bisect vs building a dict/set.

Task: on already-sorted data, compare a single O(log n) bisect lookup against
building a set (O(n)) and then querying it.

Takeaway: for a *single* (or few) lookups on sorted data, bisect wins -- you skip
the O(n) build. The set/dict wins once many lookups amortize the build cost.
Pick the structure that matches your query count.

Run: .venv/bin/python chapter_3/ex03_bisect_vs_dict/ex03_bisect_vs_dict.py
"""
import bisect
import pathlib
import random
import sys
import timeit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from perf import human  # noqa: E402


def main():
    random.seed(0)
    data = sorted(random.sample(range(10_000_000), 1_000_000))
    target = data[123_456]

    def via_bisect():
        i = bisect.bisect_left(data, target)
        return i if i < len(data) and data[i] == target else -1

    def build_then_query():
        s = set(data)          # O(n) build paid on every call here
        return target in s

    t_bisect = min(timeit.repeat(via_bisect, number=1000)) / 1000
    t_build = min(timeit.repeat(build_then_query, number=10)) / 10
    print(f"bisect lookup (no build):       {t_bisect * 1e6:8.3f} us/query")
    print(f"set build + 1 query:            {t_build * 1e3:8.3f} ms/query")
    print(f"-> build costs ~{t_build / t_bisect:,.0f}x a single bisect lookup")

    # Amortized: build once, query many times.
    s = set(data)
    t_member = min(timeit.repeat(lambda: target in s, number=1_000_000)) / 1e6
    print(f"set membership (prebuilt):      {t_member * 1e6:8.3f} us/query  <- O(1), wins at scale")

    # Memory cost of the O(1): the hash table is much larger than the sorted list.
    print("\nMemory footprint (1,000,000 ints):")
    print(f"  sorted list:  {human(sys.getsizeof(data))}  (the data, contiguous)")
    print(f"  set(data):    {human(sys.getsizeof(s))}  (hash table, ~mostly empty)")
    print(f"  -> the set trades ~{sys.getsizeof(s) / sys.getsizeof(data):.1f}x memory for O(1) lookup")


if __name__ == "__main__":
    main()
