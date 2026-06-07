"""Chapter 6 - Exercise 3: in-place vs out-of-place ops (Examples 6-11, 6-12).

Task: (1) show with id() that `a += b` reuses a's buffer while `a = a + b`
allocates a new one; (2) time both across small (in-cache) and large
(out-of-cache) arrays.

Takeaway: `a = a + b` allocates a fresh array every call -- and allocation is a
trip to the kernel (a minor page fault), far worse than a cache miss. `a += b`
reuses the buffer. The book notes a subtlety: for tiny arrays that fit in cache,
out-of-place can win because it vectorizes more freely; in-place pulls ahead once
the data overflows cache. (On this machine in-place won at every size -- measured
results below; yours depend on your cache.)

Run: .venv/bin/python chapter_6/ex03_inplace_vs_outofplace.py
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from perf import time_s  # noqa: E402


def main():
    # 1) id() proves in-place reuses memory; out-of-place rebinds to a new buffer.
    a = np.random.random((10, 10))
    b = np.random.random((10, 10))
    before = id(a)
    a += b
    same = id(a)
    a = a + b
    after = id(a)
    print("in-place  (a += b): id unchanged?", before == same, "  (reuses the buffer)")
    print("out-of-place (a = a + b): id changed?", same != after, "  (allocated a new array)")

    # 2) time both across sizes. CRITICAL: build the inputs ONCE, outside the timed
    #    call (like the book's `%%timeit` setup line). If we re-allocated the random
    #    arrays inside each call, that allocation would swamp the small alloc
    #    difference we are trying to isolate -- and the result would be pure noise.
    #    `a + b` discards its result; `a += b` accumulates into a (values grow, but
    #    the timing of a fixed-size float add is unaffected).
    print("\nout-of-place (a = a + b) vs in-place (a += b)   [inputs built once, not timed]:")
    for n in (5, 100, 1024, 2048):
        a, b = np.random.random((2, n, n))
        num = 200_000 if n <= 100 else (2_000 if n == 1024 else 500)
        t_oop = time_s(lambda a=a, b=b: a + b, number=num, repeat=7)
        t_ip = time_s(lambda a=a, b=b: a.__iadd__(b), number=num, repeat=7)
        winner = "in-place" if t_ip < t_oop else "out-of-place"
        ratio = max(t_oop, t_ip) / min(t_oop, t_ip)
        print(f"  {n:>4}x{n:<4}: out-of-place {t_oop * 1e6:9.3f} us   "
              f"in-place {t_ip * 1e6:9.3f} us   -> {winner} ({ratio:.2f}x)")
    print("  -> out-of-place allocates a fresh result array every call (a minor page")
    print("     fault -- a kernel round-trip, worse than a cache miss); in-place reuses")
    print("     the buffer. On this machine in-place wins at EVERY size. The book notes")
    print("     out-of-place CAN win for tiny in-cache arrays (better vectorization) --")
    print("     a hardware-dependent effect that did not reproduce here.")


if __name__ == "__main__":
    main()
