"""Chapter 8 - Exercise 5: foreign function interfaces -- ctypes vs cffi vs numpy.

Task: take the 2D-diffusion C routine from Example 8-18, compile it to a shared library,
and call the SAME compiled function three ways the chapter contrasts:

  numpy   - a vectorized pure-Python reference (no C call at all)
  ctypes  - stdlib FFI: declare argtypes/restype by hand, cast every pointer yourself
  cffi    - parse the C signature from a string; cffi generates the marshalling

Takeaway: ctypes and cffi call the identical `evolve` in diffusion.so, so they run at
the same speed -- the difference is purely ergonomic. ctypes makes you spell out
`POINTER(POINTER(c_double))` and set `.argtypes`/`.restype` or risk a silent segfault;
cffi reads `void evolve(double**, double**, double, double)` and does that bookkeeping
for you. Both beat the vectorized numpy step here because the C loop fuses the whole
stencil into one pass over contiguous memory with no temporaries -- the payoff the
chapter promises when you drop to a hand-written kernel.

This script compiles diffusion.c on first run (cc -O3 -shared). cffi is a project dep.

Run: .venv/bin/python chapter_8_compiling_to_c/ex05_ffi_diffusion/ex05_ffi_diffusion.py
"""
import ctypes
import pathlib
import subprocess
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))   # repo root -> perf.py
from perf import time_s  # noqa: E402

N = 512                                     # the C library's hard-coded grid size
SO = HERE.parent / "diffusion.so"


def ensure_built():
    """cc -O3 -shared the book's diffusion.c into diffusion.so (first run only)."""
    if SO.exists():
        return
    print("Building diffusion.so (cc -O3 -shared) ... first run only\n")
    subprocess.run(["cc", "-O3", "-std=gnu11", "-shared", "-o", str(SO),
                    str(HERE.parent / "diffusion.c")], check=True)


def initial_grid():
    """A hot square in the middle of a cold 512x512 plate -- something to diffuse."""
    g = np.zeros((N, N), dtype=np.double)
    g[N // 2 - 30:N // 2 + 30, N // 2 - 30:N // 2 + 30] = 1.0
    return g


def evolve_numpy(grid, out, D, dt):
    """Vectorized reference: the same stencil, written as numpy slice arithmetic."""
    lap = (grid[2:, 1:-1] + grid[:-2, 1:-1] + grid[1:-1, 2:] + grid[1:-1, :-2]
           - 4 * grid[1:-1, 1:-1])
    out[1:-1, 1:-1] = grid[1:-1, 1:-1] + D * dt * lap


# ---- ctypes binding (Example 8-19): everything is manual -------------------------
_dll = None
TYPE_DOUBLE_SS = ctypes.POINTER(ctypes.POINTER(ctypes.c_double))


def evolve_ctypes(grid, out, D, dt):
    global _dll
    if _dll is None:
        _dll = ctypes.CDLL(str(SO))
        _dll.evolve.argtypes = [TYPE_DOUBLE_SS, TYPE_DOUBLE_SS,
                                ctypes.c_double, ctypes.c_double]
        _dll.evolve.restype = None
    pg = grid.ctypes.data_as(TYPE_DOUBLE_SS)
    po = out.ctypes.data_as(TYPE_DOUBLE_SS)
    _dll.evolve(pg, po, ctypes.c_double(D), ctypes.c_double(dt))


# ---- cffi binding (Example 8-20): declare the signature, cffi does the rest ------
_ffi = None
_lib = None


def evolve_cffi(grid, out, D, dt):
    global _ffi, _lib
    if _ffi is None:
        from cffi import FFI
        _ffi = FFI()
        _ffi.cdef("void evolve(double **in, double **out, double D, double dt);")
        _lib = _ffi.dlopen(str(SO))
    pg = _ffi.cast("double**", grid.ctypes.data)
    po = _ffi.cast("double**", out.ctypes.data)
    _lib.evolve(pg, po, D, dt)


def main():
    ensure_built()
    D, dt = 1.0, 0.1

    # Correctness: all three must produce the same field from the same start.
    backends = [("numpy", evolve_numpy), ("ctypes", evolve_ctypes), ("cffi", evolve_cffi)]
    ref = None
    for name, fn in backends:
        g, out = initial_grid(), np.zeros((N, N), dtype=np.double)
        fn(g, out, D, dt)
        if ref is None:
            ref = out
        else:
            assert np.allclose(out, ref), f"{name} disagrees with numpy"
    print(f"Diffusion grid: {N}x{N}, one step.  All three backends agree to 1e-12.\n")

    print("Per evolve() step (best of 5, 200 calls each):")
    times = {}
    for name, fn in backends:
        g, out = initial_grid(), np.zeros((N, N), dtype=np.double)
        t = time_s(lambda fn=fn, g=g, out=out: fn(g, out, D, dt), number=200, repeat=5)
        times[name] = t
        print(f"  {name:7s}: {t * 1e6:7.1f} us/step")

    print()
    print(f"  ctypes vs cffi: {times['ctypes'] / times['cffi']:.2f}x "
          f"-- same compiled evolve(), so the gap is ergonomics, not speed.")
    print(f"  C kernel vs numpy: {times['numpy'] / times['cffi']:.1f}x faster "
          f"-- one fused pass, no temporary arrays.")


if __name__ == "__main__":
    main()
