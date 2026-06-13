"""Chapter 4 - Exercise 2: set vs list for uniqueness (Example 4-3).

Task: build a phone book of N unique first names and time both approaches for
several N. Confirm the speedup WIDENS with N.

Takeaway: the list version does a linear scan of a growing "seen" list per name;
the set version has no inner loop (set.add is O(1)) -> one O(n) pass. One cost
scales with data size, the other stays flat, so the ratio grows without bound.

Run: .venv/bin/python chapter_4/ex02_set_vs_list_unique/ex02_set_vs_list_unique.py
"""
import pathlib
import sys
import timeit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from perf import peak_bytes, human  # noqa: E402


def list_unique_first_names(phonebook):
    seen = []
    for name, _ in phonebook:
        first = name.split(" ", 1)[0]
        for u in seen:
            if u == first:
                break
        else:
            seen.append(first)
    return len(seen)


def set_unique_first_names(phonebook):
    seen = set()
    for name, _ in phonebook:
        seen.add(name.split(" ", 1)[0])
    return len(seen)


def main():
    print("Time (speedup widens with N):")
    for N in (1_000, 5_000, 20_000):
        pb = [(f"Name{i} Last{i}", "555") for i in range(N)]
        t_list = min(timeit.repeat(lambda: list_unique_first_names(pb), repeat=3, number=1))
        t_set = min(timeit.repeat(lambda: set_unique_first_names(pb), repeat=3, number=1))
        print(f"  N={N:>6}: list={t_list:7.4f}s  set={t_set:8.5f}s  speedup={t_list / t_set:6.0f}x")

    # Memory: both hold the unique names; the set's hash table carries slack.
    pb = [(f"Name{i} Last{i}", "555") for i in range(20_000)]
    m_list = peak_bytes(lambda: list_unique_first_names(pb))
    m_set = peak_bytes(lambda: set_unique_first_names(pb))
    print(f"\nMemory (N=20,000, peak allocated):")
    print(f"  list method: {human(m_list)}")
    print(f"  set method:  {human(m_set)}  (hash table is kept <=2/3 full, so a bit larger)")
    print("  -> the set spends modest extra memory to turn O(n) scans into O(1) adds")


if __name__ == "__main__":
    main()
