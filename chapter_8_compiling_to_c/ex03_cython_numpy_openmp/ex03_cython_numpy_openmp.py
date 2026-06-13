"""Chapter 8 - Exercise 3: Cython over numpy memoryviews, then OpenMP for free.

Task: reproduce Table 8-2's Cython rows. Two compiled functions run the SAME expanded
-math Julia loop, but now the inputs are typed `double complex[:]` memoryviews instead
of Python lists:

  serial  - one thread (Example 8-9)
  omp     - prange + nogil + schedule="guided" across all cores (Example 8-10)

Takeaway: switching lists -> memoryviews turns every zs[i] into a C memory offset, so
the dereference no longer calls into the VM. Once the loop body is fully C-level,
parallelizing it is almost free: wrap the outer range in `prange`, release the GIL, and
OpenMP fans the pixels across cores. The "guided" scheduler hands out shrinking chunks
so the cheap and expensive regions of the fractal stay balanced -- the right choice when
per-pixel work is wildly uneven.

This script BUILDS the extension on first run by shelling out to setup.py (Example 8-11)
with Homebrew's libomp wired in, then imports the compiled .so. Delete the *.so / *.c if
you edit the .pyx and want a clean rebuild.

Run: .venv/bin/python chapter_8_compiling_to_c/ex03_cython_numpy_openmp/ex03_cython_numpy_openmp.py
"""
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))   # repo root -> perf.py
sys.path.insert(0, str(HERE.parents[1]))   # chapter dir -> _julia.py
sys.path.insert(0, str(HERE.parent))       # this folder -> compiled _cyjulia_np

from perf import time_s  # noqa: E402
import _julia  # noqa: E402


def ensure_built():
    """Compile _cyjulia_np in place if there's no .so yet (the book's manual build step).

    setup.py auto-discovers the OpenMP runtime (env / this venv's torch / Homebrew), so
    there's nothing to wire up here -- we just trigger the build once."""
    if list(HERE.parent.glob("_cyjulia_np*.so")):
        return
    print("Building _cyjulia_np (Cython + numpy + OpenMP) ... first run only\n")
    subprocess.run([sys.executable, "setup.py", "build_ext", "--inplace"],
                   cwd=HERE.parent, check=True)  # show the OpenMP-discovery line


def main():
    ensure_built()
    import _cyjulia_np  # noqa: E402  (exists only after ensure_built)

    zs, cs = _julia.build_inputs_numpy()
    checksum = _julia.expected_checksum()
    maxiter = _julia.DEFAULT_MAXITER
    cores = os.cpu_count() or 1
    print(f"Julia grid: {len(zs):,} pixels, maxiter={maxiter}  "
          f"(complex128 memoryviews, {cores} cores)\n")

    assert int(_cyjulia_np.serial(maxiter, zs, cs).sum()) == checksum, "serial"
    assert int(_cyjulia_np.omp(maxiter, zs, cs).sum()) == checksum, "omp"
    print(f"Both match sum(output) == {checksum:,}\n")

    t_serial = time_s(lambda: _cyjulia_np.serial(maxiter, zs, cs), number=1, repeat=5)
    t_omp = time_s(lambda: _cyjulia_np.omp(maxiter, zs, cs), number=1, repeat=5)

    print("Cython + numpy, one 1000x1000 grid (best of 5):")
    print(f"  serial (1 thread)        : {t_serial * 1000:7.1f} ms")
    print(f"  OpenMP prange 'guided'   : {t_omp * 1000:7.1f} ms")
    print(f"  -> OpenMP speedup: {t_serial / t_omp:.1f}x on {cores} cores "
          f"(parallel efficiency {t_serial / t_omp / cores * 100:.0f}%)\n")
    print(f"  Book's Table 8-2: Cython 0.20s serial, 0.03s OpenMP. "
          f"Ours: {t_serial:.3f}s / {t_omp:.3f}s.")


if __name__ == "__main__":
    main()
