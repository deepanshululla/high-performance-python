"""Chapter 4 - Hypothesis: __slots__ shrinks the ex05 Point without changing it.

Task: ex05 gives Point a content-based __hash__/__eq__ so a set dedups
value-equal points. Each instance carries a per-instance __dict__ (~100+ B).
Replacing it with __slots__ should cut memory hard while behaving identically.

Hypothesis:
  - MEMORY: building N slotted Points uses far less heap than N dict-based ones
    (the __dict__ per instance is gone).
  - BEHAVIOR: both dedup identically in a set, and membership still works --
    correctness is untouched; only the footprint changed.

Run: .venv/bin/python chapter_4/hypothesis/h05_slots_memory/benchmark.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from perf import peak_bytes, human  # noqa: E402

N = 1_000_000


class PointDict:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __hash__(self):
        return hash((self.x, self.y))

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y


class PointSlots:
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x, self.y = x, y

    def __hash__(self):
        return hash((self.x, self.y))

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y


def build(cls):
    return [cls(i, i) for i in range(N)]


def main():
    peak_dict = peak_bytes(lambda: build(PointDict))
    peak_slots = peak_bytes(lambda: build(PointSlots))
    print(f"Peak heap building {N:,} points:\n")
    print(f"  PointDict  (per-instance __dict__): {human(peak_dict)}")
    print(f"  PointSlots (__slots__):             {human(peak_slots)}")
    print(f"  -> __slots__ uses {peak_dict/peak_slots:.2f}x less; "
          f"saved {human(peak_dict - peak_slots)} "
          f"(~{(peak_dict - peak_slots)/N:.0f} B/instance)\n")

    # Behavior is identical: value-equal points still dedup to one entry.
    for cls in (PointDict, PointSlots):
        s = {cls(1, 1), cls(1, 1), cls(2, 3)}
        print(f"  {cls.__name__}: set({{(1,1),(1,1),(2,3)}}) -> {len(s)} elems; "
              f"(1,1) in set? {cls(1, 1) in s}")
    print("  -> same dedup, same membership. __slots__ changed memory, not meaning.")
    print(f"  (note: PointSlots has no __dict__ -> hasattr __dict__: "
          f"{hasattr(PointSlots(0, 0), '__dict__')})")


if __name__ == "__main__":
    main()
