"""Chapter 3 - Exercise 6: the 48 MB experiment (Examples 3-7 / 3-8).

Task: create N small samples of k random ints, three ways, and compare total
recursive memory:
  - list comprehension  (overallocated)
  - list([...])          (headroom reclaimed)
  - tuple([...])         (no headroom + no resize bookkeeping)

Takeaway: comp > list() > tuple. Two savings stack: dropping append headroom,
then dropping the list's extra state-tracking word.

Note: holding all three at once is ~1.2 GB at N=1e6. Default N here is 200,000;
pass a different N on the command line, e.g. `... ex06... 1000000`.

Run: .venv/bin/python chapter_3/ex06_memory_comp_list_tuple.py
"""
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from perf import time_s  # noqa: E402


def total_size(obj):
    """Recursive size: container + its contents."""
    children = 0
    try:
        children = sum(total_size(item) for item in obj)
    except TypeError:
        pass
    return sys.getsizeof(obj) + children


def main(N=200_000, k=9):
    random.seed(0)
    comp = [[random.randint(0, 100) for _ in range(k)] for _ in range(N)]
    listed = [list([random.randint(0, 100) for _ in range(k)]) for _ in range(N)]
    tupled = [tuple([random.randint(0, 100) for _ in range(k)]) for _ in range(N)]

    s_comp = total_size(comp) / 1e6
    print(f"Creating {N:,} samples of {k} items each\n")
    print(f"{'':14} {'memory':>10}  {'rel':>6}   {'build time/sample':>18}")
    builders = {
        "comprehension": lambda: [random.randint(0, 100) for _ in range(k)],
        "list([...])  ": lambda: list([random.randint(0, 100) for _ in range(k)]),
        "tuple([...]) ": lambda: tuple([random.randint(0, 100) for _ in range(k)]),
    }
    data = {"comprehension": comp, "list([...])  ": listed, "tuple([...]) ": tupled}
    for name in builders:
        sz = total_size(data[name]) / 1e6
        per = time_s(builders[name], number=10_000) * 1e9  # ns per sample
        print(f"  {name} {sz:7.2f} MB  {s_comp / sz:0.3f}x   {per:8.0f} ns/sample")
    print("\nMemory: comp > list() > tuple (headroom, then bookkeeping word).")
    print("Time: tuple() build is also cheapest per sample (freelist + no resize).")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 200_000)
