"""Build the hand-written CPython extension (book Example 8-24).

    python setup.py build_ext --inplace

produces cdiffusion.cpython-*.so, importable as `from cdiffusion import evolve`.
"""
import numpy as np
from setuptools import Extension, setup

cdiffusion = Extension(
    "cdiffusion",
    sources=["python_interface.c", "cdiffusion.c"],
    extra_compile_args=["-O3", "-std=c11"],
    include_dirs=[np.get_include()],
)

setup(name="cdiffusion", version="0.1", ext_modules=[cdiffusion])
