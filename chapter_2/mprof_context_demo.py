"""Minimal demo: labeling regions of an `mprof` graph with a CONTEXT MANAGER.

The mechanism, in three facts:

1. `mprof run --python ...` injects a `profile` object (a memory_profiler
   `TimeStamper`) into builtins — you do NOT import it.
2. `profile.timestamp("label")` returns a context manager. Entering/leaving it
   records a timestamped band into the .dat file.
3. `mprof plot` draws each band as a labeled bracket on the memory-vs-time graph.

The `try/except NameError` fallback makes the script also run normally (the
context manager just does nothing when `profile` isn't injected).

Run:
    uv run mprof run --python python chapter_2/mprof_context_demo.py
    MPLBACKEND=Agg uv run mprof plot --output chapter_2/mprof_context_demo.png mprofile_*.dat
"""
import time
from contextlib import contextmanager

try:
    profile  # type: ignore[used-before-def]  # injected by `mprof run --python`
except NameError:
    class _NoTimestamp:
        @contextmanager
        def timestamp(self, name="<block>"):
            yield
    profile = _NoTimestamp()


MB = 1024 * 1024


def main():
    held = []

    # Each labeled block becomes a bracket; sleeps make the plateaus visible
    # (mprof samples RSS every 0.1 s).
    with profile.timestamp("alloc_50MB"):
        held.append(bytearray(50 * MB))
        time.sleep(0.4)

    with profile.timestamp("alloc_100MB_more"):
        held.append(bytearray(100 * MB))
        time.sleep(0.4)

    with profile.timestamp("free_the_50MB"):
        held.pop(0)            # drop the first chunk -> memory should fall ~50 MB
        time.sleep(0.4)

    with profile.timestamp("idle_hold"):
        time.sleep(0.4)        # flat line: still holding the 100 MB chunk

    print(f"done, still holding {sum(len(b) for b in held) // MB} MB")


if __name__ == "__main__":
    main()
