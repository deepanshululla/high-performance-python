"""Chapter 8 - Exercise 12: a Rust extension via PyO3 -- the modern counterpoint to C.

Task: the chapter closes with a contributed section showing Rust as the memory-safe,
thread-safe alternative to a hand-written C extension. This builds that diffusion kernel
(src/diffusion_rs/src/lib.rs) with PyO3 + the `numpy`/`ndarray` crates via maturin, and
times it against the same vectorized numpy reference used in ex05/ex10/ex11.

Takeaway: Rust reaches the same compiled-kernel speed as C, but the borrow checker
guarantees the read-only input and mutable output views can't alias, and every array index
is bounds-checked (an off-by-one panics cleanly instead of corrupting memory). The numpy
crate exposes arrays as `ndarray` views, so the kernel reads almost like the C version --
with modern tooling (Cargo, one build command) and none of ex10's manual reference
counting. Note the API shape: PyO3's `evolve(grid, dt, D=1.0)` *returns* a fresh array
rather than writing into an out-parameter, the idiomatic Rust style.

On first run this compiles the crate with `maturin develop --release` (needs cargo/rustc).

Run: .venv/bin/python chapter_8_compiling_to_c/ex12_rust_pyo3/ex12_rust_pyo3.py
"""
import os
import pathlib
import subprocess
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))   # repo root -> perf.py
from perf import time_s  # noqa: E402

N = 512
CRATE = HERE.parent / "crate"          # the Rust crate (dir name != module name, to avoid shadowing)


def ensure_built():
    """maturin-develop the Rust crate into THIS project venv if it isn't importable yet."""
    try:
        import diffusion_rs  # noqa: F401
        return
    except ImportError:
        pass
    print("Building the Rust extension with maturin develop --release ... first run only\n")
    venv_bin = pathlib.Path(sys.executable).parent
    venv_root = venv_bin.parent          # .../high_performance_python/.venv
    cargo_bin = str(pathlib.Path.home() / ".cargo" / "bin")
    # Force maturin to install into the PROJECT venv (an inherited VIRTUAL_ENV may point
    # elsewhere), and put cargo/rustc on PATH for the build.
    env = dict(os.environ,
               VIRTUAL_ENV=str(venv_root),
               PATH=os.pathsep.join([str(venv_bin), cargo_bin, os.environ.get("PATH", "")]))
    subprocess.run([str(venv_bin / "maturin"), "develop", "--release"],
                   cwd=CRATE, env=env, check=True)


def initial_grid():
    g = np.zeros((N, N), dtype=np.double)
    g[N // 2 - 30:N // 2 + 30, N // 2 - 30:N // 2 + 30] = 1.0
    return g


def evolve_numpy(grid, dt, D=1.0):
    out = np.zeros_like(grid)
    lap = (grid[2:, 1:-1] + grid[:-2, 1:-1] + grid[1:-1, 2:] + grid[1:-1, :-2]
           - 4 * grid[1:-1, 1:-1])
    out[1:-1, 1:-1] = grid[1:-1, 1:-1] + D * dt * lap
    return out


def main():
    ensure_built()
    import diffusion_rs

    D, dt = 1.0, 0.1
    grid = initial_grid()

    # Correctness: both return a fresh array; compare the fields.
    out_np = evolve_numpy(grid, dt, D)
    out_rs = diffusion_rs.evolve(grid, dt, D)
    assert np.allclose(out_np, out_rs), "Rust result disagrees with numpy"
    print(f"Diffusion {N}x{N}, one step. numpy and Rust/PyO3 agree to 1e-12.\n")

    t_np = time_s(lambda: evolve_numpy(grid, dt, D), number=200, repeat=5)
    t_rs = time_s(lambda: diffusion_rs.evolve(grid, dt, D), number=200, repeat=5)

    print("Per evolve() step (best of 5, 200 calls each):")
    print(f"  numpy (vectorized) : {t_np * 1e6:7.1f} us/step")
    print(f"  Rust via PyO3      : {t_rs * 1e6:7.1f} us/step")
    print(f"  -> Rust is {t_np / t_rs:.1f}x faster than numpy -- C-kernel class, with "
          f"compile-time memory & thread safety.")
    print("  Note: Rust allocates and returns the output array (idiomatic), unlike the C")
    print("  out-parameter style in ex05/ex10.")


if __name__ == "__main__":
    main()
