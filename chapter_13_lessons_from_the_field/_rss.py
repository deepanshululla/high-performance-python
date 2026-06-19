"""Peak resident-memory measurement, for the exercises whose point is RAM (ex06, ex09).

The repo-wide `perf.peak_bytes` uses `tracemalloc`, which only sees the Python heap — and
the allocations that matter here live in numpy C buffers `tracemalloc` never counts. So we
measure peak **resident set size** the way Chapter 12 does: `getrusage().ru_maxrss` is a
high-water mark that only rises, so each measurement runs in a fresh `spawn`-ed child
process to get a clean baseline (the programmatic version of "restart the shell, then
%memit"). `fn` must be a top-level importable function so spawn can pickle it by qualname.
"""
import gc
import multiprocessing as mp
import resource
import sys

_CTX = mp.get_context("spawn")


def _maxrss_bytes():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS reports ru_maxrss in bytes; Linux reports kibibytes.
    return rss if sys.platform == "darwin" else rss * 1024


def _worker(fn, args, kwargs, q):
    gc.collect()
    before = _maxrss_bytes()
    obj = fn(*args, **kwargs)
    after = _maxrss_bytes()
    keep = sys.getsizeof(obj) if obj is not None else 0   # keep alive past the reading
    q.put((before, after, keep))
    del obj


def peak_rss_mib(fn, *args, **kwargs):
    """Peak RSS *increment* (MiB) caused by fn(*args), measured in a fresh spawned child."""
    q = _CTX.Queue()
    p = _CTX.Process(target=_worker, args=(fn, args, kwargs, q))
    p.start()
    before, after, _ = q.get()
    p.join()
    return (after - before) / (1024 * 1024)
