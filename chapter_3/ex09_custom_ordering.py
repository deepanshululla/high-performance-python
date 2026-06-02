"""Chapter 3 - Exercise 9: make a custom object orderable for sorted search.

Task: define __eq__ and __lt__ on a Card, use functools.total_ordering to fill
in the rest, then sort a deck and binary-search it with bisect.

Takeaway: without __eq__/__lt__, custom objects compare by memory address, so
sorting/searching is meaningless. total_ordering derives <=, >, >= from
__eq__ + __lt__ (small runtime cost).

Run: .venv/bin/python chapter_3/ex09_custom_ordering.py
"""
import bisect
import pathlib
import sys
from functools import total_ordering

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from perf import time_s  # noqa: E402

RANKS = {r: i for i, r in enumerate("23456789TJQKA", start=2)}
SUITS = {s: i for i, s in enumerate("CDHS")}  # clubs < diamonds < hearts < spades


@total_ordering
class Card:
    def __init__(self, rank, suit):
        self.rank, self.suit = rank, suit

    def _key(self):
        return (RANKS[self.rank], SUITS[self.suit])

    def __eq__(self, other):
        return self._key() == other._key()

    def __lt__(self, other):
        return self._key() < other._key()

    def __repr__(self):
        return f"{self.rank}{self.suit}"


def main():
    deck = sorted(Card(r, s) for r in "23456789TJQKA" for s in "CDHS")
    print("first 8 sorted:", deck[:8])
    target = Card("K", "H")
    i = bisect.bisect_left(deck, target)
    print(f"bisect found {deck[i]} at index {i} (searching for {target})")
    assert deck[i] == target

    # Time: total_ordering's derived <= / > call __lt__/__eq__ -> a small overhead.
    a, b = Card("K", "H"), Card("Q", "S")
    t_lt = time_s(lambda: a < b, number=1_000_000)       # native __lt__
    t_ge = time_s(lambda: a >= b, number=1_000_000)      # derived by total_ordering
    print(f"\nTime: a <  b (native __lt__):      {t_lt * 1e9:6.1f} ns")
    print(f"Time: a >= b (total_ordering-derived): {t_ge * 1e9:6.1f} ns  (extra call indirection)")
    print("Memory: O(1) -- ordering adds methods, not per-instance state.")


if __name__ == "__main__":
    main()
