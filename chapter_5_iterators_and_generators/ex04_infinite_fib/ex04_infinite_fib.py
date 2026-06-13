"""Chapter 5 - Exercise 4: infinite series + early termination.

Task: write an infinite fibonacci() generator, then answer "how many Fibonacci
numbers below 5,000 are odd?" three ways -- naive, for+break, takewhile. All
must agree.

Takeaway: an infinite `while True: yield` is only ever partially evaluated --
the caller pulls until it stops. Separating generate (fibonacci) from transform
(count) makes the transform reusable over any series.

Run: .venv/bin/python chapter_5/ex04_infinite_fib/ex04_infinite_fib.py
"""
import pathlib
import sys
from itertools import takewhile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from perf import time_s  # noqa: E402


def fibonacci():
    i, j = 0, 1
    while True:
        yield i
        i, j = j, i + j


def count_naive():
    i, j, c = 0, 1, 0
    while i <= 5000:
        if i % 2:
            c += 1
        i, j = j, i + j
    return c


def count_transform():
    c = 0
    for f in fibonacci():
        if f >= 5000:
            break
        if f % 2:
            c += 1
    return c


def count_succinct():
    return sum(1 for x in takewhile(lambda x: x < 5000, fibonacci()) if x % 2)


def main():
    a, b, c = count_naive(), count_transform(), count_succinct()
    print(f"naive    : {a}")
    print(f"transform: {b}")
    print(f"succinct : {c}")
    assert a == b == c
    print("all agree")

    print("\nTime (all three are equivalent work):")
    for name, fn in (("naive", count_naive), ("transform", count_transform), ("succinct", count_succinct)):
        print(f"  {name:<9}: {time_s(fn, number=10_000) * 1e6:6.2f} us")
    print("Memory: all O(1) -- the infinite generator holds only i, j; nothing is")
    print("stored. takewhile/break terminate it, so 'infinite' is never materialized.")


if __name__ == "__main__":
    main()
