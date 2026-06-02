"""Chapter 4 - Exercise 8: dict resizing arithmetic + the shrink-on-insert quirk.

Rules: <= 2/3 full, size is a power of two, min 8, grows ~3x when too full.

Task:
  1. Compute the table size/mask needed for N keys.
  2. Show the size class progression 8, 16, 32, ...
  3. Show (via sys.getsizeof) that emptying a dict with pop() keeps the big
     table, and check whether a later insert shrinks it.

Takeaway: pop()/del only leave tombstones; the backing table is rebuilt on a
resize. The 2nd-edition book says a post-pop *insert* triggers that shrink --
but on CPython 3.12+ it no longer does (verify below!). What reliably reclaims
the memory now is rebuilding the dict, e.g. dict.copy(). This is exactly the
chapter's own lesson: re-profile your performance assumptions across CPython
versions, because the implementation changes underneath you.

Run: .venv/bin/python chapter_4/ex08_resizing.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from perf import time_s  # noqa: E402


def table_size_for(n):
    """Smallest power-of-two table that keeps n keys <= 2/3 full (min 8)."""
    need = int(n * 5 / 3) + 1          # n * (1 + 2/3) buckets
    size = 8
    while size < need:
        size <<= 1
    return size


def main():
    for n in (3, 5, 6, 10, 11, 1039):
        size = table_size_for(n)
        print(f"N={n:>5} -> table {size:>5}, mask {size - 1:#013b}")

    print("\nsize classes:", [8 << i for i in range(12)])

    print("\nshrink demo (sys.getsizeof):")
    d = {i: i for i in range(1000)}
    full = sys.getsizeof(d)
    print(f"  1000 items:               {full:>6} B")
    for i in range(999):
        d.pop(i)
    print(f"  after popping 999 items:  {sys.getsizeof(d):>6} B  (still big -- only tombstones)")
    d[10_000] = 1
    after_insert = sys.getsizeof(d)
    verdict = "shrunk!" if after_insert < full else "NO shrink on this CPython"
    print(f"  after one insert:         {after_insert:>6} B  ({verdict})")
    print(f"  dict.copy() (rebuild):    {sys.getsizeof(d.copy()):>6} B  (reliably reclaims the slack)")

    # Time: despite O(n) resizes at each power-of-two boundary, inserts amortize to O(1).
    def build(n):
        out = {}
        for i in range(n):
            out[i] = i
        return out

    for n in (100_000, 1_000_000):
        per = time_s(lambda: build(n), number=1, repeat=3) / n * 1e9
        print(f"\nTime: building a {n:>9,}-key dict = {per:5.1f} ns/insert "
              f"(flat across sizes -> amortized O(1))")


if __name__ == "__main__":
    main()
