"""Shared multiprocessing knobs for Chapter 10.

The single most important machine fact for this chapter: on macOS with CPython
3.14, `multiprocessing.get_start_method()` is **"spawn"**, not the **"fork"** that
the book implicitly assumes (it was written on Linux, where fork is the default).

Why that matters everywhere: the book's examples routinely share state by reading
a *module global* inside a worker (a filled `numpy` array, a `RawValue` flag, an
`mmap` block). Under `fork`, the child is a copy-on-write clone of the parent, so
those globals are simply *there*. Under `spawn`, the child is a brand-new
interpreter that re-imports your module from scratch — the globals are back at
their import-time defaults, and the sharing silently evaporates.

So every exercise that relies on inherited state asks for an explicit **fork**
context via `CTX` below, which reproduces the book on this machine. The
`hypothesis/h01_fork_vs_spawn` lab is where we pull that thread on purpose and
measure both the startup-cost difference and the broken-inheritance failure.

This box has 10 physical cores and **no hyperthreading** (logical == physical),
so the book's "hyperthreads add little" story has nothing to reproduce — instead
we get clean near-linear scaling up to 10 workers and a flat line past it.
"""
import multiprocessing as mp
import os

# Explicit fork context: a copy-on-write clone of the parent, so module globals
# (filled arrays, flags) are inherited — the behaviour the book assumes.
CTX = mp.get_context("fork")

DEFAULT_START_METHOD = mp.get_start_method()      # "spawn" on this machine
N_PHYSICAL = os.cpu_count()                        # 10 here (no SMT to distinguish)
N_LOGICAL = os.cpu_count()
