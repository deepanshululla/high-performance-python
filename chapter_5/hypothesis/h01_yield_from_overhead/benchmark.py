"""Chapter 5 - Hypothesis: `yield from` is faster than manual re-yielding.

Task: ex06/ex08 build pipelines with `yield from`. The hand-written equivalent
is `for x in sub: yield x`. They look the same; are they?

Hypothesis: `yield from sub` delegates at the C level -- the outer generator is
suspended and `sub` drives the loop directly -- so it skips a Python-level
next()/resume round-trip per item. The manual `for ... : yield x` pays that
round-trip every item, so it is meaningfully slower (expect ~1.3-2x).

Run: .venv/bin/python chapter_5/hypothesis/h01_yield_from_overhead/benchmark.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from perf import time_s  # noqa: E402

N = 1_000_000


def inner(n):
    for i in range(n):
        yield i


def via_yield_from(n):
    yield from inner(n)


def via_manual(n):
    for x in inner(n):
        yield x


def main():
    t_yf = time_s(lambda: sum(via_yield_from(N)), number=1, repeat=7)
    t_manual = time_s(lambda: sum(via_manual(N)), number=1, repeat=7)
    print(f"Consuming {N:,} items through one delegating layer:\n")
    print(f"  yield from inner(n):       {t_yf*1e3:7.1f} ms   ({t_yf/N*1e9:5.1f} ns/item)")
    print(f"  for x in inner(n): yield x {t_manual*1e3:7.1f} ms   ({t_manual/N*1e9:5.1f} ns/item)")
    print(f"\n-> yield from is {t_manual/t_yf:.2f}x faster: it delegates in C and skips")
    print("   the per-item Python next()/resume the manual loop pays.")


if __name__ == "__main__":
    main()
