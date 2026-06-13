"""Chapter 8 - Exercise 11: calling Fortran from Python with f2py.

Task: Fortran is still the gold standard for vector math (LAPACK, BLAS are Fortran), and
f2py -- part of numpy -- turns a Fortran subroutine into an importable Python module almost
for free, because Fortran's explicit types let it auto-generate the whole interface. This
builds the book's Example 8-22 diffusion subroutine and calls it from Python.

Takeaway: f2py reads the `!f2py intent(...)` annotations and hands you a clean
`evolve(grid, next_grid, D, dt)` -- the grid sizes are inferred and hidden, no manual
casting like ctypes, no boilerplate like the CPython extension (ex10). The one catch the
chapter flags: Fortran stores arrays **column-major**, so you must pass numpy arrays built
with `order="F"` or you'll pay a transpose (or read the wrong data). Speed lands in the
same C-kernel league as ex05/ex10 -- the value here is the frictionless interface, not a
new speed tier.

Builds diffusion.f90 into a module on first run via `python -m numpy.f2py` (needs gfortran).

Run: .venv/bin/python chapter_8_compiling_to_c/ex11_f2py_fortran/ex11_f2py_fortran.py
"""
import os
import pathlib
import subprocess
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))   # repo root -> perf.py
sys.path.insert(0, str(HERE.parent))       # this folder -> compiled diffusion_f

from perf import time_s  # noqa: E402

N = 512


def ensure_built():
    """f2py-compile diffusion.f90 into the importable module diffusion_f (first run only)."""
    if list(HERE.parent.glob("diffusion_f*.so")):
        return
    print("Building diffusion_f from Fortran via f2py (gfortran) ... first run only\n")
    # f2py's meson backend shells out to `meson`/`ninja`, which live in the venv's bin
    # dir -- make sure that's on PATH for the build subprocess.
    venv_bin = str(pathlib.Path(sys.executable).parent)
    env = dict(os.environ, PATH=venv_bin + os.pathsep + os.environ.get("PATH", ""))
    subprocess.run([sys.executable, "-m", "numpy.f2py", "-c", "-m", "diffusion_f",
                    "diffusion.f90"], cwd=HERE.parent, check=True, env=env,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def initial_grid(order):
    g = np.zeros((N, N), dtype=np.double, order=order)
    g[N // 2 - 30:N // 2 + 30, N // 2 - 30:N // 2 + 30] = 1.0
    return g


def evolve_numpy(grid, out, D, dt):
    lap = (grid[2:, 1:-1] + grid[:-2, 1:-1] + grid[1:-1, 2:] + grid[1:-1, :-2]
           - 4 * grid[1:-1, 1:-1])
    out[1:-1, 1:-1] = grid[1:-1, 1:-1] + D * dt * lap


def main():
    ensure_built()
    from diffusion_f import evolve as evolve_f

    D, dt = 1.0, 0.1

    # Correctness: numpy reference vs Fortran (note the order="F" arrays for Fortran).
    g_np, o_np = initial_grid("C"), np.zeros((N, N), dtype=np.double)
    evolve_numpy(g_np, o_np, D, dt)
    g_f, o_f = initial_grid("F"), np.zeros((N, N), dtype=np.double, order="F")
    evolve_f(g_f, o_f, D, dt)
    assert np.allclose(o_np, o_f), "Fortran result disagrees with numpy"
    print(f"Diffusion {N}x{N}, one step. numpy and f2py-Fortran agree to 1e-12.\n")

    t_np = time_s(lambda: evolve_numpy(g_np, o_np, D, dt), number=200, repeat=5)
    t_f = time_s(lambda: evolve_f(g_f, o_f, D, dt), number=200, repeat=5)

    print("Per evolve() step (best of 5, 200 calls each):")
    print(f"  numpy (vectorized) : {t_np * 1e6:7.1f} us/step")
    print(f"  Fortran via f2py   : {t_f * 1e6:7.1f} us/step")
    print(f"  -> Fortran is {t_np / t_f:.1f}x faster than numpy -- C-kernel class, "
          f"reached through an interface f2py generated for us.")
    print("  The annotations made the sizes N/M invisible; order='F' kept the layout honest.")


if __name__ == "__main__":
    main()
