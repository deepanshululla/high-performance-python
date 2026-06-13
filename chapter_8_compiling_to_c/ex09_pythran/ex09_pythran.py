"""Chapter 8 - Exercise 9: Pythran -- AOT numpy, two low-effort compilers head to head.

Task: the chapter lists Pythran as an ahead-of-time compiler for numpy scientists that
"produces speedups very similar to Cython for much less work," driven by a single
`#pythran export` comment. This exercise compiles the same Julia loop with Pythran and
times it against Numba (ex04's JIT) -- the two "near-zero-annotation" compilers in the
chapter, one AOT, one JIT.

Takeaway: Pythran reaches Cython/Numba-class speed from a single export line and a plain
numpy-style function, with no `.pyx`, no C types, and no decorator. Its cost model is the
mirror image of Numba's: Pythran pays its compile *once, at build time* (run the `pythran`
CLI), so there's no per-process cold start -- the trade Numba makes in the other
direction. Same destination, opposite schedule for the toll.

Builds julia_pythran.py into a .so on first run via the `pythran` CLI.

Run: .venv/bin/python chapter_8_compiling_to_c/ex09_pythran/ex09_pythran.py
"""
import pathlib
import subprocess
import sys
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))   # repo root -> perf.py
sys.path.insert(0, str(HERE.parents[1]))   # chapter dir -> _julia.py
sys.path.insert(0, str(HERE.parent))       # this folder -> compiled pythran module

from perf import time_s  # noqa: E402
import _julia  # noqa: E402


def ensure_built():
    """Run the `pythran` CLI to AOT-compile julia_pythran.py (first run only)."""
    if list(HERE.parent.glob("julia_pythran*.so")):
        return
    pythran = pathlib.Path(sys.executable).parent / "pythran"
    print("Compiling julia_pythran.py with the pythran CLI (-O3) ... first run only\n")
    subprocess.run([str(pythran), str(HERE.parent / "julia_pythran.py"), "-O3"],
                   cwd=HERE.parent, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def make_numba():
    """Build the Numba equivalent for a same-script comparison."""
    from numba import jit

    @jit(nopython=True)
    def calc(maxiter, zs, cs, output):
        for i in range(len(zs)):
            n = 0
            z = zs[i]
            c = cs[i]
            while n < maxiter and (z.real * z.real + z.imag * z.imag) < 4:
                z = z * z + c
                n += 1
            output[i] = n
    return calc


def main():
    ensure_built()
    import julia_pythran  # noqa: E402

    zs, cs = _julia.build_inputs_numpy()
    checksum = _julia.expected_checksum()
    maxiter = _julia.DEFAULT_MAXITER

    # Pythran: no warm-up needed -- it was compiled at build time.
    out_p = julia_pythran.calc(maxiter, zs, cs)
    assert int(out_p.sum()) == checksum, "pythran wrong result"
    t_pythran = time_s(lambda: julia_pythran.calc(maxiter, zs, cs), number=1, repeat=5)

    # Numba: pay the JIT cold start, then time warm.
    numba_calc = make_numba()
    out_n = np.empty(len(zs), dtype=np.int32)
    t0 = time.perf_counter()
    numba_calc(maxiter, zs, cs, out_n)
    t_numba_cold = time.perf_counter() - t0
    assert int(out_n.sum()) == checksum, "numba wrong result"
    t_numba_warm = time_s(lambda: numba_calc(maxiter, zs, cs, out_n), number=1, repeat=5)

    print(f"Julia grid: {len(zs):,} pixels, maxiter={maxiter}.  Both match the checksum.\n")
    print("One 1000x1000 grid (best of 5):")
    print(f"  Pythran  (AOT, compiled at build time) : {t_pythran * 1000:6.1f} ms")
    print(f"  Numba    warm (JIT, after cold start)  : {t_numba_warm * 1000:6.1f} ms")
    print(f"  Numba    cold (first call, for context): {t_numba_cold * 1000:6.1f} ms\n")
    print(f"  Pythran vs Numba-warm: {t_numba_warm / t_pythran:.2f}x "
          f"-- same class of speed, both for almost no annotation.")
    print("  The difference is *when* you pay the compiler: Pythran at build, Numba at first call.")


if __name__ == "__main__":
    main()
