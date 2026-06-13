"""Chapter 8 - Exercise 4: Numba @jit -- cold start, warm runs, and free parallelism.

Task: reproduce Table 8-2's Numba rows on the same Julia workload. Add ONE decorator,
`@jit(nopython=True)`, to a plain-numpy loop and measure three things the chapter calls
out:

  cold   - the very first call, which pays the LLVM compile cost (the JIT "cold start")
  warm   - the second and later calls, reusing the compiled machine code
  par    - @jit(parallel=True) + prange, warm, fanned across cores

Takeaway: Numba matches hand-annotated Cython for almost no effort -- no .pyx, no types,
no setup.py -- but the first call is dramatically slower because compilation happens at
runtime, on the actual argument types. That cold start is paid fresh in every new
process, which is exactly why the chapter warns against JITs for short, frequently
relaunched scripts. Once warm, swapping `range` -> `prange` and `parallel=True` buys
multicore for two tokens.

Run: .venv/bin/python chapter_8_compiling_to_c/ex04_numba_jit/ex04_numba_jit.py
"""
import os
import pathlib
import sys
import time

import numpy as np
from numba import jit, prange

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))   # repo root -> perf.py
sys.path.insert(0, str(HERE.parents[1]))   # chapter dir -> _julia.py
from perf import time_s  # noqa: E402
import _julia  # noqa: E402


@jit(nopython=True)
def calc_numba(maxiter, zs, cs, output):
    """Serial Julia loop, expanded math. Numba infers every type on first call."""
    for i in range(len(zs)):
        n = 0
        z = zs[i]
        c = cs[i]
        while n < maxiter and (z.real * z.real + z.imag * z.imag) < 4:
            z = z * z + c
            n += 1
        output[i] = n


@jit(nopython=True, parallel=True)
def calc_numba_par(maxiter, zs, cs, output):
    """Same loop; prange + parallel=True let Numba's threading layer split the pixels."""
    for i in prange(len(zs)):
        n = 0
        z = zs[i]
        c = cs[i]
        while n < maxiter and (z.real * z.real + z.imag * z.imag) < 4:
            z = z * z + c
            n += 1
        output[i] = n


def main():
    zs, cs = _julia.build_inputs_numpy()
    checksum = _julia.expected_checksum()
    maxiter = _julia.DEFAULT_MAXITER
    cores = os.cpu_count() or 1
    out = np.empty(len(zs), dtype=np.int32)
    print(f"Julia grid: {len(zs):,} pixels, maxiter={maxiter}  "
          f"(complex128 arrays, Numba {__import__('numba').__version__}, {cores} cores)\n")

    # COLD: the first call compiles for (int, complex128[:], complex128[:], int32[:]).
    t0 = time.perf_counter()
    calc_numba(maxiter, zs, cs, out)
    t_cold = time.perf_counter() - t0
    assert int(out.sum()) == checksum, "serial numba wrong result"

    # WARM: machine code is cached for these types; no recompile.
    t_warm = time_s(lambda: calc_numba(maxiter, zs, cs, out), number=1, repeat=5)

    # PARALLEL: separate function => its own cold compile, then warm.
    out_p = np.empty(len(zs), dtype=np.int32)
    t0 = time.perf_counter()
    calc_numba_par(maxiter, zs, cs, out_p)
    t_par_cold = time.perf_counter() - t0
    assert int(out_p.sum()) == checksum, "parallel numba wrong result"
    t_par = time_s(lambda: calc_numba_par(maxiter, zs, cs, out_p), number=1, repeat=5)

    print("Numba on one 1000x1000 grid:")
    print(f"  @jit  cold (1st call, compiling) : {t_cold * 1000:8.1f} ms")
    print(f"  @jit  warm (best of 5)           : {t_warm * 1000:8.1f} ms")
    print(f"  @jit(parallel) cold (1st call)   : {t_par_cold * 1000:8.1f} ms  "
          f"(compile + threading-layer init)")
    print(f"  @jit(parallel) warm (best of 5)  : {t_par * 1000:8.1f} ms  "
          f"({t_warm / t_par:.1f}x over serial, {cores} cores)\n")
    print(f"  cold/warm ratio: {t_cold / t_warm:.0f}x  "
          f"-- the whole compile cost is paid on call #1, then gone.")
    print(f"  Book's Table 8-2: Numba 0.19s warm, 0.05s parallel. "
          f"Ours: {t_warm:.3f}s / {t_par:.3f}s.")


if __name__ == "__main__":
    main()
