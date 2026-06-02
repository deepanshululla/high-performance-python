"""Chapter 4 - Exercise 1: hash-then-mask by hand.

A dict index is hash(key) & (size - 1), with size a power of two.

Task:
  1. Where does a key hashing to 28975 land in an 8-bucket table? In 512?
  2. Using a first-letter hash, do Rome and Barcelona collide in a 4-element
     dict (8 buckets, mask 0b111)?

Takeaway: masking keeps only the LOW bits of the hash, so keys sharing low bits
collide even though their full hashes differ.

Run: .venv/bin/python chapter_4/ex01_hash_mask.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from perf import time_s  # noqa: E402


def bucket(hash_value, size):
    return hash_value & (size - 1)


def main():
    print("key hashing to 28975:")
    print(f"  8 buckets  (mask 0b111):       index {bucket(28975, 8)}")
    print(f"  512 buckets(mask 0b1_1111_1111): index {bucket(28975, 512)}\n")

    rome = ord("R")
    barca = ord("B")
    print(f"ord('R')={rome} & 0b111 = {bucket(rome, 8)}")
    print(f"ord('B')={barca} & 0b111 = {bucket(barca, 8)}")
    print("collide!" if bucket(rome, 8) == bucket(barca, 8) else "no collision")

    # Time/Memory: the index step is one bitwise AND -> O(1), no allocation.
    key = "some example key"
    t_mask = time_s(lambda: hash(key) & 1023, number=10_000_000)
    print(f"\nTime: hash(key) & mask = {t_mask * 1e9:.1f} ns/op  (O(1), one AND)")
    print("Memory: O(1) -- the index is computed, nothing is stored to find it.")


if __name__ == "__main__":
    main()
