"""Chapter 5 - Exercise 5: itertools workflow drills.

Solve each lazily (no full materialization):
  1. First 5 items of an infinite generator.
  2. Concatenate range(3) then range(100, 103).
  3. Repeat [1, 2, 3] forever, take the first 7.
  4. Take items while below 100, then stop.

Takeaway: islice slices, chain glues, cycle makes finite->infinite, takewhile
adds a stop condition -- none build the full sequence.

Run: .venv/bin/python chapter_5/ex05_itertools_drills/ex05_itertools_drills.py
"""
import pathlib
import sys
from itertools import islice, chain, cycle, takewhile, count

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from perf import peak_bytes, time_s, human  # noqa: E402


def main():
    print("islice(count(), 5)            ->", list(islice(count(), 5)))
    print("chain(range(3), range(100,103))->", list(chain(range(3), range(100, 103))))
    print("islice(cycle([1,2,3]), 7)     ->", list(islice(cycle([1, 2, 3]), 7)))
    print("takewhile(<100, count(0, 25)) ->", list(takewhile(lambda x: x < 100, count(0, 25))))

    # Memory + time: summing a lazy islice vs first materializing a list.
    N = 1_000_000
    lazy = lambda: sum(islice(count(), N))
    eager = lambda: sum(list(range(N)))
    print(f"\nSum first {N:,} integers:")
    print(f"  lazy  sum(islice(count(), N)): {time_s(lazy, number=3) * 1e3:6.1f} ms   peak {human(peak_bytes(lazy))}")
    print(f"  eager sum(list(range(N))):     {time_s(eager, number=3) * 1e3:6.1f} ms   peak {human(peak_bytes(eager))}")
    print("  -> itertools composition stays O(1) memory; materializing is O(n)")


if __name__ == "__main__":
    main()
