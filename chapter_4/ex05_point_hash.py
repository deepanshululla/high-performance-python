"""Chapter 4 - Exercise 5: content-based hashing so a set deduplicates.

Task: by default Point(1,1) and another Point(1,1) are distinct in a set
(hash = id). Give Point a content-based __hash__ + __eq__ so value-equal points
collapse.

Takeaway: __hash__ puts value-equal objects in the same bucket; __eq__ confirms
the match on probe. Defining __eq__ WITHOUT __hash__ makes the class unhashable.

Run: .venv/bin/python chapter_4/ex05_point_hash.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from perf import time_s  # noqa: E402


class PointDefault:
    def __init__(self, x, y):
        self.x, self.y = x, y


class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __hash__(self):
        return hash((self.x, self.y))   # reuse the tuple hash

    def __eq__(self, other):
        return (self.x, self.y) == (other.x, other.y)


def main():
    a, b = PointDefault(1, 1), PointDefault(1, 1)
    print(f"default hash: set has {len({a, b})} elements (id-based -> no dedup)")

    p1, p2 = Point(1, 1), Point(1, 1)
    s = {p1, p2}
    print(f"content hash: set has {len(s)} element  (deduped)")
    print(f"Point(1,1) in set? {Point(1, 1) in s}")
    assert len(s) == 1 and Point(1, 1) in s

    # Time: a content hash costs a tuple hash per call (vs the trivial id() hash).
    p = Point(3, 4)
    t_hash = time_s(lambda: hash(p), number=10_000_000)
    print(f"\nTime: content __hash__ = {t_hash * 1e9:.1f} ns/op  (hashes the (x, y) tuple)")
    print("Memory: O(1) per object; correctness (dedup) is the goal, not speed.")
    print("Trade-off: the hash must stay O(1) or every set/dict op inherits its cost.")


if __name__ == "__main__":
    main()
