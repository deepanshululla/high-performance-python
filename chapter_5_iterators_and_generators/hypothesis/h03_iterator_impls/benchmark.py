"""Chapter 5 - Hypothesis: native generators beat a hand-rolled __next__ class.

Task: ex01 notes a generator *is* its own iterator. There are three common ways
to build an iterator over a sequence:
  1. generator function (`def ...: yield`)
  2. generator expression (`(i for i in ...)`)
  3. a class implementing __iter__/__next__

Hypothesis: (1) and (2) are roughly equal and fast (suspend/resume handled by
the C-level generator machinery), while (3) is markedly slower (3-5x): every
item pays a Python-level __next__ call plus attribute loads/stores on self.

Run: .venv/bin/python chapter_5/hypothesis/h03_iterator_impls/benchmark.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from perf import time_s  # noqa: E402

N = 1_000_000


def gen_func(n):
    i = 0
    while i < n:
        yield i
        i += 1


def gen_expr(n):
    return (i for i in range(n))


class GenClass:
    def __init__(self, n):
        self.i = 0
        self.n = n

    def __iter__(self):
        return self

    def __next__(self):
        if self.i >= self.n:
            raise StopIteration
        v = self.i
        self.i += 1
        return v


def main():
    variants = [
        ("generator function", lambda: sum(gen_func(N))),
        ("generator expression", lambda: sum(gen_expr(N))),
        ("class __iter__/__next__", lambda: sum(GenClass(N))),
    ]
    print(f"Summing {N:,} items, three iterator implementations:\n")
    print("   implementation             time       ns/item")
    results = []
    for name, fn in variants:
        t = time_s(fn, number=1, repeat=7)
        results.append((name, t))
        print(f"  {name:<26} {t*1e3:6.1f} ms   {t/N*1e9:6.1f}")

    fastest = min(results, key=lambda r: r[1])[1]
    cls_t = results[-1][1]
    print(f"\n-> the __next__ class is {cls_t/fastest:.1f}x slower than the fastest")
    print("   generator: per-item Python method call + self attribute access is the tax")
    print("   the C-level generator machinery avoids.")


if __name__ == "__main__":
    main()
