"""Resident-memory measurement for the "Using Less RAM" chapter.

The repo-wide `perf.peak_bytes` uses `tracemalloc`, which only sees the *Python
heap*. That is exactly the wrong tool for this chapter: a numpy array, a marisa
trie, or a scipy sparse matrix keeps almost all of its bytes in C-level buffers
that `tracemalloc` never counts. To talk honestly about RAM we have to ask the
operating system how big the process actually got — which is what the book's
`%memit` magic does by sampling the process RSS.

So we measure peak **resident set size** instead, and we do it the way the book
recommends: in a freshly started interpreter. `getrusage(...).ru_maxrss` is a
high-water mark that only ever rises, so once a 3.8 GB allocation has happened
inside a process, every later measurement in that same process is poisoned. The
book sidesteps this by telling you to "exit and restart the Python shell"; we do
the programmatic equivalent by running each allocation in its own `spawn`-ed
child process, reading that child's peak RSS, and throwing the child away.

    from _mem import peak_rss_mib
    mib = peak_rss_mib(build_a_big_thing, 100_000_000)

`build_a_big_thing` must be a top-level (importable) function, because `spawn`
pickles it by qualified name to ship it to the child. Keep any heavy work inside
functions, not at module top level, or the child will pay for it at import time.
"""
import gc
import multiprocessing as mp
import resource
import sys

# A fresh interpreter per measurement gives each allocation a clean RSS baseline,
# the same reason the book says to restart the shell between %memit calls.
_CTX = mp.get_context("spawn")


def _maxrss_bytes():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS reports ru_maxrss in bytes; Linux reports it in kibibytes.
    return rss if sys.platform == "darwin" else rss * 1024


def _worker(fn, args, kwargs, q):
    gc.collect()
    before = _maxrss_bytes()
    obj = fn(*args, **kwargs)            # the allocation we want to weigh
    after = _maxrss_bytes()
    # Touch + keep the object alive until *after* we read the high-water mark, so
    # a lazy structure (np.zeros!) can't get measured before it is realised.
    keep = sys.getsizeof(obj) if obj is not None else 0
    q.put((before, after, keep))
    del obj


def peak_rss_bytes(fn, *args, **kwargs):
    """Peak RSS *increment* (bytes) caused by fn(*args), measured in a fresh child.

    Returns the rise in the child's resident high-water mark across the call —
    the same quantity `%memit` prints as "increment". Because the child starts
    clean, the baseline is just a bare interpreter plus whatever fn imports.
    """
    q = _CTX.Queue()
    p = _CTX.Process(target=_worker, args=(fn, args, kwargs, q))
    p.start()
    before, after, _ = q.get()
    p.join()
    return after - before


def peak_rss_mib(fn, *args, **kwargs):
    """peak_rss_bytes in mebibytes (MiB), the unit the book's %memit reports."""
    return peak_rss_bytes(fn, *args, **kwargs) / (1024 * 1024)
