"""Chapter 3 - Hypothesis: preallocating a list beats append-growing it.

Task: ex05 shows append-growth pays repeated resize+copy. The book (ch6,
"Aren't Python Lists Good Enough?") advises preallocating. Test it directly.

Hypothesis (build N ints three ways):
  - TIME: list(range(N)) fastest (C loop, exact alloc); [None]*N + index-assign
    second (no resize, no method lookup -- index store beats append call);
    append loop slowest (resize copies + per-item LOAD_METHOD/append).
  - MEMORY: append leaves overallocation headroom; prealloc and list(range)
    are exact (and equal).

Run: .venv/bin/python chapter_3/hypothesis/h02_preallocation_vs_append/benchmark.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from perf import time_s, peak_bytes, human  # noqa: E402

N = 1_000_000


def build_append():
    out = []
    for i in range(N):
        out.append(i)
    return out


def build_prealloc():
    out: list = [None] * N
    for i in range(N):
        out[i] = i
    return out


def build_listrange():
    return list(range(N))


def main():
    variants = [
        ("append loop", build_append),
        ("[None]*N + assign", build_prealloc),
        ("list(range(N))", build_listrange),
    ]
    print(f"Building a {N:,}-int list three ways:\n")
    print("  method                time        peak mem     result size")
    base = None
    for name, fn in variants:
        t = time_s(fn, number=1, repeat=5)
        peak = peak_bytes(fn)
        size = sys.getsizeof(fn())
        if base is None:
            base = t
        print(f"  {name:<20} {t*1e3:7.1f} ms   {human(peak):>9}   {human(size):>9}")
    print()
    t_app = time_s(build_append, number=1, repeat=5)
    t_pre = time_s(build_prealloc, number=1, repeat=5)
    t_lr = time_s(build_listrange, number=1, repeat=5)
    print(f"-> prealloc is {t_app/t_pre:.2f}x faster than append; "
          f"list(range) is {t_app/t_lr:.2f}x faster.")
    print("-> prealloc/list(range) allocate exactly N; append carries dead headroom.")


if __name__ == "__main__":
    main()
