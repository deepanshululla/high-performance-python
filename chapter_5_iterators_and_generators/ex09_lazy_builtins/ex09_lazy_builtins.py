"""Chapter 5 - Exercise 9: which built-ins are already lazy?

Task: classify range, map, zip, filter, reversed, enumerate, sorted, list,
dict.items as lazy or eager. Show that zip(range(1e5), range(1e5)) holds only
the current pair in memory.

Takeaway: map/zip/filter/reversed/enumerate are lazy iterators; range is a lazy
range type; sorted/list/dict-construction are eager (must materialize).
dict.items() is a lazy *view*.

Run: .venv/bin/python chapter_5/ex09_lazy_builtins/ex09_lazy_builtins.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from perf import peak_bytes, human  # noqa: E402


def main():
    samples = {
        "range(3)": range(3),
        "map": map(str, [1, 2]),
        "zip": zip([1], [2]),
        "filter": filter(None, [0, 1]),
        "reversed([..])": reversed([1, 2, 3]),
        "enumerate([..])": enumerate([9]),
        "sorted([..])": sorted([3, 1, 2]),
        "list([..])": list([1, 2]),
        "{}.items()": {1: 2}.items(),
    }
    for name, obj in samples.items():
        lazy = not isinstance(obj, (list, tuple))
        kind = type(obj).__name__
        print(f"  {name:<16} -> {kind:<14} {'lazy' if lazy else 'EAGER (materialized)'}")

    # zip holds only the current pair, not the whole product.
    z = zip(range(100_000), range(100_000))
    print("\nfirst pair from a 100k zip:", next(z), "(only two numbers ever live in memory)")

    # Memory: consuming a lazy map vs materializing it into a list.
    N = 1_000_000
    lazy = lambda: sum(map(lambda x: x * 2, range(N)))      # never stores the doubled values
    eager = lambda: sum(list(map(lambda x: x * 2, range(N))))  # builds a 1M list first
    print(f"\nSum 2*x for x in range({N:,}):")
    print(f"  sum(map(...)):       peak {human(peak_bytes(lazy))}  (lazy, O(1))")
    print(f"  sum(list(map(...))): peak {human(peak_bytes(eager))}  (materialized, O(n))")


if __name__ == "__main__":
    main()
