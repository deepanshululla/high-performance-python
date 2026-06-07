"""Chapter 6 - Exercise 6: numeric precision on the CPU (Example 6-21, numpy part).

Task: time `a*a + a` for a 2048x2048 array as float64, float32, and float16, and
report the per-element storage. This is the CPU half of the book's precision
experiment (the GPU half needs torch, which isn't installed here).

Takeaway: lower precision is NOT automatically faster on a CPU. float32 usually
beats float64 (half the data on the bus, native instructions). But float16 has
no native CPU instructions, so numpy must up-convert every element -- making it
*slower* than float64. On a GPU the story flips: float16 is ~4x faster because
the silicon was built to trade precision for throughput.

Run: .venv/bin/python chapter_6/ex06_float_precision_cpu.py
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from perf import time_s, human  # noqa: E402

N = 2048


def main():
    print(f"a*a + a on a {N}x{N} array, by dtype:")
    base = None
    for dt in (np.float64, np.float32, np.float16):
        a = np.random.rand(N, N).astype(dt)

        def work(a=a):
            return a * a + a

        t = time_s(work, number=10, repeat=3)
        if base is None:
            base = t
        rel = base / t
        tag = f"{rel:4.2f}x vs float64" if rel >= 1 else f"{1 / rel:4.2f}x SLOWER than float64"
        itemsize = np.dtype(dt).itemsize
        print(f"  {dt.__name__:8}: {t * 1e3:8.2f} ms   {tag:>22}   "
              f"storage {itemsize} B/elem ({human(itemsize * N * N)} total)")

    print("\n  -> float32 is faster (less data to move, native instructions).")
    print("     float16 is typically SLOWER on the CPU: no native float16 ops, so")
    print("     numpy converts every element up to compute, then back down.")
    print("     Lower precision is a performance *knob* on the GPU but a *penalty* here.")


if __name__ == "__main__":
    main()
