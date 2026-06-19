"""ex01 — the price of wrapping every number in a Python object.

The chapter's opening lesson: a `list` of N *distinct* integers stores N pointers
to N separately heap-allocated `int` objects, each carrying ~28 bytes of reference
count, type pointer, and GC bookkeeping on top of its value. An `array.array` or a
`numpy` array instead packs the raw 8-byte primitives into one contiguous buffer,
with no per-element Python object at all.

We build the same N integers four ways and weigh each one's peak resident memory
in a freshly started child process (see `_mem.py` — `tracemalloc` would miss the
numpy/array C buffers entirely). The list should cost several times what the two
primitive buffers do. We also include `np.zeros`, which famously reports almost
nothing because its pages are allocated lazily on first write — a profiling trap
the book calls out explicitly.
"""
import array
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir -> _mem

import numpy as np  # noqa: E402

from _mem import peak_rss_mib  # noqa: E402

N = 100_000_000   # the book's 1e8; the list of these costs gigabytes


def build_list(n=N):
    """N distinct Python int objects behind N pointers — the expensive way."""
    return [i for i in range(n)]


def build_array(n=N):
    """N raw 8-byte signed ints in one contiguous buffer (array module)."""
    return array.array("q", range(n))


def build_numpy(n=N):
    """N int64 primitives in one numpy buffer — eagerly filled."""
    return np.arange(n, dtype=np.int64)


def build_numpy_zeros(n=N):
    """np.zeros: lazily allocated, so it misreports as near-zero until written."""
    return np.zeros(n, dtype=np.int64)


def measure(n=N):
    """Return {label: peak RSS increment in MiB} for each construction."""
    return {
        "list": peak_rss_mib(build_list, n),
        "array('q')": peak_rss_mib(build_array, n),
        "numpy int64": peak_rss_mib(build_numpy, n),
        "np.zeros (lazy)": peak_rss_mib(build_numpy_zeros, n),
    }


def main():
    m = measure()
    print(f"peak RSS to hold {N:,} integers, measured in a fresh process each:")
    for label, mib in m.items():
        print(f"  {label:18}: {mib:8.1f} MiB")
    ratio = m["list"] / m["numpy int64"]
    print(f"\nlist / numpy ratio: {ratio:.1f}x  "
          f"(every Python int carries ~28 bytes of object overhead)")
    print("note: np.zeros looks free because its pages are allocated lazily on "
          "first write — np.ones or np.arange pay the cost up front.")


if __name__ == "__main__":
    main()
