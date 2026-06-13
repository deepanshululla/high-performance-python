"""Chapter 8 - Exercise 1: the pure-Python Julia baseline, and a strength-reduction trap.

Task: run the book's CPU-bound Julia-set generator (Example 8-1) in plain CPython --
the reference number every compiler in this chapter is measured against. Then test a
claim the book makes only *inside* Cython: that replacing `abs(z) < 2` with the
algebraically equal `z.real*z.real + z.imag*z.imag < 4` (dropping a sqrt) is faster.

Takeaway (measured, and it overturns the naive reading): in the *interpreter* the
expanded form is ~1.8x SLOWER, not faster. `abs(z)` on a complex is one optimized
builtin call; the expanded form is several attribute lookups (`.real`, `.imag`) plus
Python-level multiplies and adds, each its own trip through the VM. Strength reduction
only wins once the loop is *compiled* (ex02/ex03/ex04), where `re*re+im*im` becomes a
few machine instructions and `abs` would call libm's sqrt. The lesson is the chapter's
own: the same source change can be a pessimization in one engine and a 2x win in
another -- so you measure on the engine you'll actually ship.

Run: .venv/bin/python chapter_8_compiling_to_c/ex01_julia_baseline/ex01_julia_baseline.py
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))   # repo root -> perf.py
sys.path.insert(0, str(HERE.parents[1]))   # chapter dir -> _julia.py
from perf import time_s  # noqa: E402
import _julia  # noqa: E402

MAXITER = _julia.DEFAULT_MAXITER


def calc_abs(maxiter, zs, cs):
    """The book's original inner loop: escape test via abs(z) < 2 (one builtin call)."""
    output = [0] * len(zs)
    for i in range(len(zs)):
        n = 0
        z = zs[i]
        c = cs[i]
        while n < maxiter and abs(z) < 2:
            z = z * z + c
            n += 1
        output[i] = n
    return output


def calc_expanded(maxiter, zs, cs):
    """'Strength-reduced' loop: square both sides so abs(z) < 2 becomes re^2+im^2 < 4.

    Mathematically cheaper (no sqrt), but in the interpreter it's *more* bytecode.
    """
    output = [0] * len(zs)
    for i in range(len(zs)):
        n = 0
        z = zs[i]
        c = cs[i]
        while n < maxiter and (z.real * z.real + z.imag * z.imag) < 4:
            z = z * z + c
            n += 1
        output[i] = n
    return output


def main():
    zs, cs = _julia.build_inputs()
    checksum = _julia.expected_checksum()
    print(f"Julia grid: {len(zs):,} pixels, maxiter={MAXITER}  (book's 1000x1000 problem)")

    # Correctness first: both forms must produce the book's anchor sum.
    out_abs = calc_abs(MAXITER, zs, cs)
    out_exp = calc_expanded(MAXITER, zs, cs)
    assert sum(out_abs) == checksum, sum(out_abs)
    assert out_abs == out_exp, "expanded math must match abs() exactly"
    print(f"Both forms agree and match the book's checksum sum(output) == {checksum:,}\n")

    # Time each (one full grid per round; min of 3 rounds). This is the slow path --
    # a few seconds a round -- so keep the round count low.
    t_abs = time_s(lambda: calc_abs(MAXITER, zs, cs), number=1, repeat=3)
    t_exp = time_s(lambda: calc_expanded(MAXITER, zs, cs), number=1, repeat=3)

    print("Pure CPython 3.14, one 1000x1000 grid (best of 3):")
    print(f"  abs(z) < 2                       : {t_abs:6.2f} s   <- the chapter's baseline")
    print(f"  re^2 + im^2 < 4  (expanded math) : {t_exp:6.2f} s")
    slower = t_exp / t_abs
    verb = "SLOWER" if slower > 1 else "faster"
    print(f"  -> in the interpreter the 'optimization' is {slower:.2f}x {verb}: "
          f"abs() is one builtin call,")
    print(f"     the expanded form is many bytecodes. The win is real only once COMPILED.\n")

    print("Baseline carried into the rest of the chapter:")
    print(f"  ex02 (Cython), ex03 (Cython+numpy/OpenMP), ex04 (Numba) all divide into ~{t_abs:.1f}s.")
    print(f"  Watch the expanded form flip from a loss here to a ~2x win there.")


if __name__ == "__main__":
    main()
