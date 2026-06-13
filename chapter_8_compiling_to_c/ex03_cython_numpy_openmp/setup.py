"""Build _cyjulia_np with numpy headers and OpenMP, mirroring the book's Example 8-11.

Apple clang doesn't ship an OpenMP runtime. Rather than force a system `brew install
libomp`, we auto-discover an `omp.h` + `libomp` from, in order: the LIBOMP_PREFIX env
var, this venv's PyTorch (which bundles both), then the usual Homebrew locations. The
chosen lib dir is also baked in as an rpath so the compiled .so finds libomp at runtime.

If no OpenMP runtime is found, we build *without* the openmp flags: Cython guards its
prange with `#ifdef _OPENMP`, so the `omp` function still compiles -- it just runs
single-threaded. That keeps the exercise runnable everywhere, OpenMP or not.

Build in place:
    python setup.py build_ext --inplace
"""
import glob
import os

import numpy as np
from setuptools import Extension, setup
from Cython.Build import cythonize


def find_openmp():
    """Return (include_dir, lib_dir) of a usable OpenMP runtime, or None."""
    cands = []
    if os.environ.get("LIBOMP_PREFIX"):
        p = os.environ["LIBOMP_PREFIX"]
        cands.append((f"{p}/include", f"{p}/lib"))
    try:                                   # this venv's torch bundles omp.h + libomp
        import torch
        td = os.path.dirname(torch.__file__)
        cands.append((os.path.join(td, "include"), os.path.join(td, "lib")))
    except ImportError:
        pass
    cands += [("/opt/homebrew/opt/libomp/include", "/opt/homebrew/opt/libomp/lib"),
              ("/usr/local/opt/libomp/include", "/usr/local/opt/libomp/lib")]
    for inc, lib in cands:
        if os.path.exists(os.path.join(inc, "omp.h")) and glob.glob(os.path.join(lib, "libomp*")):
            return inc, lib
    return None


omp = find_openmp()
if omp:
    inc, lib = omp
    if os.environ.get("OMP_PLAIN"):        # gcc/Linux style
        compile_args = ["-fopenmp", "-O3"]
        link_args = ["-fopenmp"]
    else:                                  # Apple clang + a discovered libomp
        compile_args = ["-Xpreprocessor", "-fopenmp", f"-I{inc}", "-O3"]
        link_args = [f"-L{lib}", "-lomp", f"-Wl,-rpath,{lib}",
                     "-Wl,-headerpad_max_install_names"]
    print(f"setup.py: OpenMP runtime found at {lib}")
else:
    compile_args = ["-O3"]                  # serial fallback; prange degrades gracefully
    link_args = []
    print("setup.py: no OpenMP runtime found -- building serial (omp() will be 1-thread)")

ext = Extension(
    "_cyjulia_np",
    ["_cyjulia_np.pyx"],
    extra_compile_args=compile_args,
    extra_link_args=link_args,
    include_dirs=[np.get_include()],
)

setup(name="_cyjulia_np", ext_modules=cythonize([ext], language_level=3))


def _fix_macos_libomp_path():
    """Point the built .so at the real libomp.

    A discovered libomp (e.g. PyTorch's) often records an absolute install-name like
    /opt/llvm-openmp/lib/libomp.dylib that doesn't exist on this machine, so an rpath
    alone won't resolve it. Rewrite that dependency to the actual dylib we found.
    """
    import subprocess
    import sys
    if omp is None or sys.platform != "darwin":
        return
    _, lib = omp
    if not os.path.exists(os.path.join(lib, "libomp.dylib")):
        return
    # Resolve via the rpath we linked in (-Wl,-rpath,{lib}); @rpath/libomp.dylib is
    # shorter than the bogus absolute install-name, so it always fits the load command.
    target = "@rpath/libomp.dylib"
    for so in glob.glob("_cyjulia_np*.so"):
        listing = subprocess.check_output(["otool", "-L", so], text=True)
        for line in listing.splitlines()[1:]:
            dep = line.strip().split(" ")[0]
            if "libomp" in dep and dep != target:
                subprocess.run(["install_name_tool", "-change", dep, target, so], check=True)
                print(f"setup.py: rebound {os.path.basename(so)} libomp -> {target} (via rpath {lib})")


_fix_macos_libomp_path()
