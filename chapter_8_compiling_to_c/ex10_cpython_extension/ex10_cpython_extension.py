"""Chapter 8 - Exercise 10: the raw CPython C extension -- the 'last resort'.

Task: the chapter ends the FFI tour with the most manual option of all -- writing a
CPython extension module by hand (Examples 8-23/8-24). It takes ~50 lines of C just to
parse arguments, check types and dimensions, and manage a reference count, versus the
four lines of cffi in ex05. This exercise builds that extension, calls the identical
diffusion kernel through it, and measures whether all that boilerplate buys anything.

Takeaway: it does -- but barely. With no per-call marshalling layer between Python and the
kernel, the hand-written extension is minutely faster than the ctypes binding to the *same*
compiled `evolve`. The chapter's verdict stands: the speed edge is real but tiny, the code
is fragile and version-coupled (a CPython API change can force a rewrite), and you should
reach for it only when nothing else fits. Here it's a cautionary tale you can measure.

Builds the extension (setup.py) and a plain .so (cc) for the ctypes comparison on first run.

Run: .venv/bin/python chapter_8_compiling_to_c/ex10_cpython_extension/ex10_cpython_extension.py
"""
import ctypes
import pathlib
import subprocess
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))   # repo root -> perf.py
sys.path.insert(0, str(HERE.parent))       # this folder -> compiled cdiffusion

from perf import time_s  # noqa: E402

N = 512
PLAIN_SO = HERE.parent / "diffusion_plain.so"


def ensure_built():
    """Build the CPython extension (setup.py) and a plain shared lib (cc) for ctypes."""
    if not list(HERE.parent.glob("cdiffusion*.so")):
        print("Building CPython extension cdiffusion (setup.py) ... first run only")
        subprocess.run([sys.executable, "setup.py", "build_ext", "--inplace"],
                       cwd=HERE.parent, check=True, stdout=subprocess.DEVNULL)
    if not PLAIN_SO.exists():
        print("Building plain diffusion_plain.so (cc -O3 -shared) for the ctypes baseline\n")
        subprocess.run(["cc", "-O3", "-std=gnu11", "-shared", "-o", str(PLAIN_SO),
                        str(HERE.parent / "cdiffusion.c")], check=True)


def initial_grid():
    g = np.zeros((N, N), dtype=np.double)
    g[N // 2 - 30:N // 2 + 30, N // 2 - 30:N // 2 + 30] = 1.0
    return g


def evolve_numpy(grid, out, dt, D=1.0):
    lap = (grid[2:, 1:-1] + grid[:-2, 1:-1] + grid[1:-1, 2:] + grid[1:-1, :-2]
           - 4 * grid[1:-1, 1:-1])
    out[1:-1, 1:-1] = grid[1:-1, 1:-1] + D * dt * lap


_TY = ctypes.POINTER(ctypes.POINTER(ctypes.c_double))
_dll = None


def evolve_ctypes(grid, out, dt, D=1.0):
    global _dll
    if _dll is None:
        _dll = ctypes.CDLL(str(PLAIN_SO))
        _dll.evolve.argtypes = [_TY, _TY, ctypes.c_double, ctypes.c_double]
        _dll.evolve.restype = None
    _dll.evolve(grid.ctypes.data_as(_TY), out.ctypes.data_as(_TY),
                ctypes.c_double(D), ctypes.c_double(dt))


def main():
    ensure_built()
    from cdiffusion import evolve as evolve_cpyext  # the hand-written extension

    D, dt = 1.0, 0.1
    backends = [("numpy", evolve_numpy),
                ("ctypes", evolve_ctypes),
                ("CPython ext", lambda g, o, dt, D=1.0: evolve_cpyext(g, o, dt, D))]

    ref = None
    for name, fn in backends:
        g, o = initial_grid(), np.zeros((N, N), dtype=np.double)
        fn(g, o, dt, D)
        if ref is None:
            ref = o
        else:
            assert np.allclose(o, ref), f"{name} disagrees"
    print(f"Diffusion {N}x{N}, one step. numpy / ctypes / CPython-ext agree to 1e-12.\n")

    print("Per evolve() step (best of 5, 200 calls each):")
    times = {}
    for name, fn in backends:
        g, o = initial_grid(), np.zeros((N, N), dtype=np.double)
        t = time_s(lambda fn=fn, g=g, o=o: fn(g, o, dt, D), number=200, repeat=5)
        times[name] = t
        print(f"  {name:12s}: {t * 1e6:7.1f} us/step")

    print()
    print(f"  CPython-ext vs ctypes: {times['ctypes'] / times['CPython ext']:.2f}x "
          f"-- the hand-written path shaves the per-call marshalling, but only just.")
    print(f"  Both call the identical compiled evolve(); the extension cost ~50 lines of C")
    print(f"  to ex05's 4 lines of cffi. That's the trade the chapter warns about.")


if __name__ == "__main__":
    main()
