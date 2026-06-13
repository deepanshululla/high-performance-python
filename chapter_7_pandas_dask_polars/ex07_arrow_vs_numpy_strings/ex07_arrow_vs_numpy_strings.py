"""Chapter 7 - Exercise 7: Arrow vs NumPy storage for strings (Arrow and NumPy section).

Task: store the same low-cardinality string column three ways -- the default NumPy
`object` dtype, PyArrow-backed `string[pyarrow]`, and pandas `category` -- and compare RAM.
Then store a numeric column under NumPy and Arrow to show the numeric break-even.

Takeaway: NumPy's object strings store a full Python `str` per cell (every duplicate
repeated, each object scattered on the heap), which is enormous for repeated values.
Arrow keeps a compact columnar buffer; `category` goes furthest for genuinely low
cardinality by storing each distinct value once plus small integer codes. For numeric
columns Arrow and NumPy are essentially a wash -- which is why a sane default is "NumPy for
numbers, Arrow for strings".

Run: .venv/bin/python chapter_7/ex07_arrow_vs_numpy_strings/ex07_arrow_vs_numpy_strings.py
"""
import pathlib
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from perf import human  # noqa: E402

warnings.filterwarnings("ignore")

N = 200_000
CATEGORIES = ["type_a", "type_b", "type_c", "yes", "no"]


def string_memory(n=N, seed=0):
    """RAM for a low-cardinality string column under three storage backends."""
    rng = np.random.default_rng(seed)
    vals = rng.choice(CATEGORIES, size=n)
    return {
        "object (NumPy)": pd.Series(vals, dtype="object").memory_usage(deep=True),
        "string[pyarrow]": pd.Series(vals, dtype="string[pyarrow]").memory_usage(deep=True),
        "category": pd.Series(vals, dtype="category").memory_usage(deep=True),
    }


def numeric_memory(n=N, seed=1):
    """RAM for a float column under NumPy vs Arrow -- expected to roughly tie."""
    rng = np.random.default_rng(seed)
    vals = rng.random(n)
    return {
        "float64 (NumPy)": pd.Series(vals, dtype="float64").memory_usage(deep=True),
        "double[pyarrow]": pd.Series(vals, dtype="double[pyarrow]").memory_usage(deep=True),
    }


def main():
    strs = string_memory()
    base = strs["object (NumPy)"]
    print(f"Low-cardinality string column ({N:,} rows, {len(CATEGORIES)} distinct values):")
    for name, mem in strs.items():
        print(f"  {name:16s}: {human(mem):>9s}   ({base / mem:4.1f}x smaller than object)")
    print("  -> object repeats a full Python str per cell; Arrow packs a columnar buffer;")
    print("     category stores each distinct value once plus tiny integer codes.")

    nums = numeric_memory()
    nbase = nums["float64 (NumPy)"]
    print(f"\nNumeric column ({N:,} float64 values):")
    for name, mem in nums.items():
        print(f"  {name:16s}: {human(mem):>9s}   ({nbase / mem:4.2f}x)")
    print("  -> numbers are a near tie, so default to NumPy for numerics, Arrow for strings.")
    print("     (Stay on Arrow when loading from Parquet -- Parquet IS Arrow internally.)")


if __name__ == "__main__":
    main()
