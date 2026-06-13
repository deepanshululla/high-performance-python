"""Chapter 4 - Exercise 3: phone-book lookup, dict vs list-bisect.

Task: time a list+bisect lookup (O(log n)) against a dict lookup (O(1)) as N
grows. Watch the ratio increase with N.

Takeaway: the dict stays flat (O(1)); the bisect lookup grows like log n, so
the dict pulls further ahead as N grows -- once you do enough lookups to repay
the O(n) dict build.

Run: .venv/bin/python chapter_4/ex03_dict_vs_bisect/ex03_dict_vs_bisect.py
"""
import bisect
import pathlib
import random
import sys
import timeit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from perf import human  # noqa: E402


def build(N):
    names = sorted(f"person{i:07d}" for i in range(N))
    numbers = [str(random.randint(10 ** 9, 10 ** 10)) for _ in names]
    return names, numbers, dict(zip(names, numbers))


def lookup_bisect(names, numbers, key):
    i = bisect.bisect_left(names, key)
    return numbers[i] if i < len(names) and names[i] == key else None


def main():
    random.seed(0)
    print("Time (dict O(1) stays flat; bisect O(log n) grows):")
    last = None
    for N in (1_000, 100_000, 1_000_000):
        names, numbers, d = build(N)
        key = names[N // 2]
        tb = min(timeit.repeat(lambda: lookup_bisect(names, numbers, key), repeat=5, number=10_000))
        td = min(timeit.repeat(lambda: d[key], repeat=5, number=10_000))
        print(f"  N={N:>9,}: bisect={tb:7.4f}  dict={td:7.4f}  ratio={tb / td:5.1f}x")
        last = (names, numbers, d, N)

    # Memory: the dict's O(1) costs a hash table on top of the key/value data.
    names, numbers, d, N = last
    lists_bytes = sys.getsizeof(names) + sys.getsizeof(numbers)
    print(f"\nMemory (N={N:,}):")
    print(f"  list + bisect (names+numbers): {human(lists_bytes)}")
    print(f"  dict:                          {human(sys.getsizeof(d))} (table only; +the same strings)")
    print("  -> dict buys flat O(1) lookup; bisect buys lower memory at O(log n)")


if __name__ == "__main__":
    main()
