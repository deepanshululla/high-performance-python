"""Tiny self-contained timing + memory helpers for the chapter exercises.

Importable from any chapter_*/exNN_*.py via:

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    from perf import time_s, peak_bytes, human

Memory is measured with `tracemalloc` (Python-heap allocations) so every script
self-reports memory without needing `python -m memory_profiler`. tracemalloc
numbers are smaller than RSS (they exclude interpreter overhead) but are
reproducible and isolate the allocation the exercise cares about.
"""
import gc
import timeit
import tracemalloc


def time_s(fn, number=1, repeat=5):
    """Best per-call wall-clock time in seconds (min of `repeat` rounds)."""
    return min(timeit.repeat(fn, number=number, repeat=repeat)) / number


def peak_bytes(fn):
    """Peak Python-heap bytes allocated during one call to `fn`."""
    gc.collect()
    tracemalloc.start()
    fn()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak


def human(nbytes):
    n = float(nbytes)
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
