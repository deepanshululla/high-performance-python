"""Chapter 7 - Exercise 6: a single NaN promotes an int Series to float (NaN section).

Task: drop one missing value into an integer Series and watch its dtype. Compare the
default NumPy-backed `int64` (which silently becomes `float64`) against pandas' nullable
`Int64` (capital I), which keeps the integers exact and stores missingness in a side mask.

Takeaway: NaN is a float-only bit pattern in NumPy -- an `int64` has no spare encoding for
"missing", so pandas must recast the whole column to `float64` to hold it. Above 2^53 a
float64 can no longer represent consecutive integers, so large ids silently lose precision.
The nullable `Int64` escapes this by pairing the integers with a separate Boolean NaN-mask.

Run: .venv/bin/python chapter_7/ex06_nan_int_promotion/ex06_nan_int_promotion.py
"""
import pathlib
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from perf import human  # noqa: E402

warnings.filterwarnings("ignore")

N = 100_000


def memories(n=N):
    """RAM (bytes) for the same integers under int64, the promoted float64, and Int64."""
    s_int = pd.Series(range(n), dtype="int64")
    s_float = s_int.astype("float64").copy()
    s_float.iloc[0] = np.nan
    s_null = pd.Series(range(n), dtype="Int64")
    s_null.iloc[0] = pd.NA
    return {
        "int64": s_int.memory_usage(deep=True),
        "float64\n(promoted)": s_float.memory_usage(deep=True),
        "Int64\n(+mask)": s_null.memory_usage(deep=True),
    }


def main():
    # 1) The promotion. A NumPy-backed int64 Series cannot hold NaN, so it becomes float64.
    s_int = pd.Series(range(N), dtype="int64")
    s_with_nan = s_int.astype("float64").copy()
    s_with_nan.iloc[0] = np.nan
    print("Default NumPy-backed integers:")
    print(f"  start dtype           : {s_int.dtype}")
    print(f"  after one NaN          : {s_with_nan.dtype}   <- promoted, no opt-out")

    # 2) The nullable Int64 keeps integers exact, marking the hole in a separate mask.
    s_nullable = pd.Series(range(N), dtype="Int64")
    s_nullable.iloc[0] = pd.NA
    print("\nNullable pandas Int64 (capital I):")
    print(f"  dtype after pd.NA      : {s_nullable.dtype}   <- stays integer")
    print(f"  the missing entry      : {s_nullable.iloc[0]!r}")

    # 3) The precision cost of the float promotion: 2^53 is the last safe integer.
    big = 2 ** 53 + 1
    as_float = int(np.float64(big))
    print("\nWhy promotion can corrupt data:")
    print(f"  2^53 + 1 = {big}")
    print(f"  through float64 -> {as_float}   ({'LOST' if as_float != big else 'ok'}: floats can't")
    print("  represent every integer past 2^53, so large ids round to a neighbour.)")

    # 4) Memory: the nullable type carries a 1-byte mask per element on top of the int64.
    mem_int = s_int.memory_usage(deep=True)
    mem_float = s_with_nan.memory_usage(deep=True)
    mem_null = s_nullable.memory_usage(deep=True)
    print(f"\nMemory for {N:,} elements:")
    print(f"  int64 (no NaN possible) : {human(mem_int)}")
    print(f"  float64 (post-promotion): {human(mem_float)}")
    print(f"  Int64 (int + NaN-mask)  : {human(mem_null)}   <- +1 byte/element for the mask")
    print("  -> the mask is the price of keeping integers exact AND NaN-aware.")


if __name__ == "__main__":
    main()
