"""ex08 — sharing one numpy array across processes, with no copy.

The book shares a 30.5 GB array across eight CPUs by allocating the bytes once
with `multiprocessing.Array` and wrapping a `numpy` view around them, so every
worker reads and writes the *same* physical memory instead of receiving a pickled
copy. We do the same at a laptop-friendly size and prove the no-copy claim three
ways.

The recipe:

1. `multiprocessing.Array(c_double, n, lock=False)` allocates a shared block of
   bytes (lock=False because we partition the work so no two workers touch the
   same row — we don't need synchronization).
2. `np.frombuffer(...).reshape(...)` wraps that block as a 2-D array without
   copying; `arr.base.base is shared_base` confirms the view points back at the
   shared bytes.
3. Each worker overwrites one row with its own PID. First it asserts the cell
   still holds the parent's fill value (42), which can only be true if it is
   looking at the parent's memory, not a fresh zero-filled copy.

This leans entirely on fork inheritance: the workers reach the array as a module
global. Under macOS's default spawn start method the global would be re-imported
empty and the demo would fail its own assert — which is exactly why we force a
fork context (see _mp.py and the h01 hypothesis).
"""
import ctypes
import os
import pathlib
import sys
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[0]))

from perf import human  # noqa: E402
from _mp import CTX  # noqa: E402

SIZE_A, SIZE_B = 1000, 40_000     # 40M doubles = 320 MB, rows divisible by 8 workers
DEFAULT_VALUE = 42
NBR_OF_PROCESSES = 8

# Shared bytes -> numpy view, as module globals so forked workers inherit them.
_shared_base = CTX.Array(ctypes.c_double, SIZE_A * SIZE_B, lock=False)
main_nparray = np.frombuffer(_shared_base, dtype=ctypes.c_double).reshape(SIZE_A, SIZE_B)  # type: ignore[call-overload]


def worker_fn(idx):
    """Overwrite row idx with this process's PID, after proving it's shared memory."""
    # If this is really the parent's array, the row still holds the fill value.
    assert main_nparray[idx, 0] == DEFAULT_VALUE
    main_nparray[idx, :] = os.getpid()


def run():
    """Fill the array in the parent, overwrite it in parallel, verify, and time it."""
    assert main_nparray.base.base is _shared_base, "numpy view is not backed by shared bytes"
    main_nparray.fill(DEFAULT_VALUE)

    t0 = time.time()
    with CTX.Pool(NBR_OF_PROCESSES) as pool:
        pool.map(worker_fn, range(SIZE_A))
    elapsed = time.time() - t0

    # Verify with np.unique (fast) rather than the book's Counter (slow over 40M).
    pids, counts = np.unique(main_nparray, return_counts=True)
    assert DEFAULT_VALUE not in pids, "some cells were never written"
    assert int(counts.sum()) == SIZE_A * SIZE_B, "lost some cells"
    assert len(pids) == NBR_OF_PROCESSES, f"expected {NBR_OF_PROCESSES} PIDs, got {len(pids)}"
    return elapsed, dict(zip(pids.astype(int), counts.astype(int)))


def main():
    elapsed, pid_counts = run()
    one = main_nparray.nbytes
    print(f"shared numpy array: {SIZE_A} x {SIZE_B} = {main_nparray.size:,} doubles "
          f"({human(one)})")
    print(f"  filled in parallel by {NBR_OF_PROCESSES} processes in {elapsed:.2f}s")
    print(f"  no-copy verified : arr.base.base is the shared block")
    print(f"  each worker wrote {SIZE_A // NBR_OF_PROCESSES} rows; PID -> cells:")
    for pid, count in sorted(pid_counts.items()):
        print(f"    pid {pid}: {count:,} cells")
    print(f"  shared footprint : {human(one)} (one copy)")
    print(f"  a copy per worker would have cost: {human(one * NBR_OF_PROCESSES)} "
          f"({NBR_OF_PROCESSES}x) and the time to pickle it across {NBR_OF_PROCESSES} pipes")


if __name__ == "__main__":
    main()
