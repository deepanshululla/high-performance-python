"""Chapter 4 - Exercise 7: why twoletter_hash is ideal, and when it isn't.

Task:
  1. Show the hash is distinct for every lowercase pair (a bijection onto 0..675).
  2. With a 2,048-bucket table (11-bit mask) there are zero collisions.
  3. With a 512-bucket table (9-bit mask) collisions appear.

Takeaway: "ideal" is relative to table size. You must know the value range AND
the table size to design a collision-free hash.

Run: .venv/bin/python chapter_4/ex07_twoletter_hash/ex07_twoletter_hash.py
"""
import string
from collections import Counter


def twoletter_hash(key):
    offset = ord("a")
    k1, k2 = key
    return (ord(k2) - offset) + 26 * (ord(k1) - offset)


def collisions(size):
    mask = size - 1
    buckets = Counter()
    for a in string.ascii_lowercase:
        for b in string.ascii_lowercase:
            buckets[twoletter_hash(a + b) & mask] += 1
    return sum(c - 1 for c in buckets.values() if c > 1)


def main():
    raw = {twoletter_hash(a + b) for a in string.ascii_lowercase for b in string.ascii_lowercase}
    print(f"distinct raw hashes for 676 pairs: {len(raw)} (range {min(raw)}..{max(raw)})")
    for size in (2048, 1024, 512):
        print(f"table size {size:>5} (mask {size - 1:#015b}): {collisions(size)} collisions")
    print("-> collision-free while every value fits below the mask; wraps once it doesn't")


if __name__ == "__main__":
    main()
