"""Chapter 8 - Exercise 2: compiling the pure-Python Julia loop with Cython.

Task: reproduce Table 8-1 -- the "no numpy" column -- by walking up four rungs of the
same loop, each compiled by Cython, and timing the jump each one buys:

  v0  unannotated, just run through Cython            (Example 8-3)
  v1  cdef the hot scalars to C types, abs() escape   (Example 8-7)
  v2  v1 + expanded math (re*re + im*im < 4)          (Example 8-8)
  v3  v2 + boundscheck/wraparound disabled            (the book's final tweak)

Takeaway: typing the scalars is the big lever -- it moves the z/n updates out of the
VM and into C. The expanded math, which was a *loss* in pure Python (ex01), now flips
to a win because the compiled form is a few machine ops while abs() calls libm sqrt.
Disabling bounds checks does ~nothing: the inputs are still Python lists, so each
zs[i] dereference goes through the VM no matter what -- which is exactly the wall ex03
breaks through with numpy memoryviews.

The .pyx next to this file is compiled on first import by pyximport; the first run
therefore pays a one-time C-compile cost (look for a short pause), later runs reuse
the cached .so.

Run: .venv/bin/python chapter_8_compiling_to_c/ex02_cython_pure_python/ex02_cython_pure_python.py
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))   # repo root -> perf.py
sys.path.insert(0, str(HERE.parents[1]))   # chapter dir -> _julia.py
sys.path.insert(0, str(HERE.parent))       # this folder -> _cyjulia.pyx

from perf import time_s  # noqa: E402
import _julia  # noqa: E402

import pyximport  # noqa: E402
pyximport.install(language_level=3)
import _cyjulia  # noqa: E402  (triggers the Cython build on first import)

MAXITER = _julia.DEFAULT_MAXITER


def main():
    zs, cs = _julia.build_inputs()
    checksum = _julia.expected_checksum()
    print(f"Julia grid: {len(zs):,} pixels, maxiter={MAXITER}  (Python lists, no numpy)\n")

    rungs = [
        ("v0  unannotated (compiled as-is)", _cyjulia.v0_plain),
        ("v1  cdef C types, abs(z) < 2     ", _cyjulia.v1_typed),
        ("v2  v1 + expanded math           ", _cyjulia.v2_expanded),
        ("v3  v2 + boundscheck=False        ", _cyjulia.v3_nobounds),
    ]

    # Correctness: every rung must reproduce the book's anchor sum.
    for name, fn in rungs:
        assert sum(fn(MAXITER, zs, cs)) == checksum, name
    print(f"All four rungs match sum(output) == {checksum:,}\n")

    print("Cython, one 1000x1000 grid (best of 5):")
    times = {}
    for name, fn in rungs:
        t = time_s(lambda fn=fn: fn(MAXITER, zs, cs), number=1, repeat=5)
        times[name.split()[0]] = t
        print(f"  {name}: {t:6.3f} s")

    print()
    print(f"  typing alone (v0 -> v1):     {times['v0'] / times['v1']:5.1f}x")
    print(f"  expanded math (v1 -> v2):    {times['v1'] / times['v2']:5.2f}x")
    print(f"  bounds off (v2 -> v3):       {times['v2'] / times['v3']:5.2f}x  (expected ~1x on lists)")
    print(f"\n  Book's Table 8-1: Cython 0.43s (typed), 0.23s (expanded). "
          f"Ours: {times['v1']:.3f}s / {times['v2']:.3f}s.")


if __name__ == "__main__":
    main()
