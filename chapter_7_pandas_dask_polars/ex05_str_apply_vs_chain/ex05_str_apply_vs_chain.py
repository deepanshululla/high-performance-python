"""Chapter 7 - Exercise 5: chained str ops vs a single apply (Example 7-12).

Task: find the position of the first digit '9' after the decimal point in a string column,
two ways -- a chain of pandas `.str` accessors (`split(expand=True)` then `find`) versus a
plain Python function pushed through `apply`.

Takeaway: the `.str` chain has to build several intermediate pandas objects (the
`expand=True` split alone materializes a whole new DataFrame), while `apply(find_9)` does
all the string work one row at a time with no new pandas objects. The apply form is also
trivially unit-testable and parallelizable (ex08).

Note: on pandas 3.0 (Copy-on-Write by default) the gap is narrower than the book's ~3x --
CoW removed many of the defensive copies the chain used to pay for. The ordering still holds.

Run: .venv/bin/python chapter_7/ex05_str_apply_vs_chain/ex05_str_apply_vs_chain.py
"""
import pathlib
import sys
import timeit
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

warnings.filterwarnings("ignore")

ROWS = 50_000


def gen_str_series(n_rows=ROWS, seed=0):
    """A column of numbers rendered as strings, e.g. '1.0166666666666666'."""
    rng = np.random.default_rng(seed)
    vals = rng.poisson(60, size=n_rows) / 60.0
    return pd.Series(vals).apply(lambda v: str(v))


def find_9(s):
    """Plain Python: return -1 if '9' is absent after the decimal point, else its index."""
    return s.split(".")[1].find("9")


def via_str_chain(series):
    return series.str.split(".", expand=True)[1].str.find("9")


def via_apply(series):
    return series.apply(find_9)


def main():
    s = gen_str_series()

    assert np.array_equal(via_str_chain(s).to_numpy(), via_apply(s).to_numpy())
    print(f"Both approaches agree on all {len(s):,} positions.")
    print(f"Sample: {s.iloc[0]!r} -> first '9' after '.' at index {find_9(s.iloc[0])}\n")

    n = 20
    t_chain = timeit.timeit(lambda: via_str_chain(s), number=n) / n
    t_apply = timeit.timeit(lambda: via_apply(s), number=n) / n

    print(f"Locating the first '9' across {len(s):,} strings:")
    print(f"  .str chain (split+find) : {t_chain * 1e3:6.1f} ms   (1.0x)")
    print(f"  apply(find_9)           : {t_apply * 1e3:6.1f} ms   ({t_chain / t_apply:.1f}x faster)")
    print("  -> the chain builds intermediate pandas objects (expand=True -> a DataFrame);")
    print("     apply does the work per row with no new pandas objects, and is unit-testable.")


if __name__ == "__main__":
    main()
