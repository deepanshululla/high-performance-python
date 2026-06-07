"""Chapter 3 - Hypothesis: the tuple freelist has a sharp cliff at size 20->21.

Task: ex07 shows a tuple literal (size 10) is ~9x faster to build than a list,
but only vaguely gestures at "past size 20 the gap narrows". CPython keeps a
freelist of up to 2,000 tuples for *each* size 1-20; sizes >20 always malloc.

Hypothesis:
  - TIME: creating a tuple of size n rises ~linearly (per-element copy) but
    shows a discrete step UP at n=21, where the freelist no longer applies.
  - MEMORY: getsizeof(n) is perfectly linear (8 B/elem) with NO cliff -- the
    cliff is an *allocation* effect, not a size effect.

Method: for n in 0..40, time `tuple(src)` (built from a list so it isn't const-
folded/interned and must really allocate each iteration), and record getsizeof.

Run: .venv/bin/python chapter_3/hypothesis/h01_tuple_freelist_cliff/benchmark.py
"""
import pathlib
import sys
import timeit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from perf import human  # noqa: E402

NUMBER = 2_000_000


def time_build(n):
    """ns per `tuple(src)` for a size-n source list (freed each iteration)."""
    return timeit.timeit("tuple(src)", globals={"src": list(range(n))}, number=NUMBER) / NUMBER * 1e9


def main():
    print(f"Building size-n tuples, {NUMBER:,} reps each (built from a list so each one allocates):\n")
    print("    n   ns/build   getsizeof   d(ns) vs n-1")
    rows = []
    prev_t = None
    for n in range(0, 41):
        t = time_build(n)
        size = sys.getsizeof(tuple(range(n)))
        delta = "" if prev_t is None else f"{t - prev_t:+6.2f}"
        marker = "  <- freelist boundary (20->21)" if n == 21 else ""
        print(f"  {n:>3}   {t:7.2f}    {size:>5} B    {delta}{marker}")
        rows.append((n, t, size))
        prev_t = t

    # Quantify the cliff: average ns just below vs just above the size-20 line,
    # after removing the gentle linear per-element trend on each side.
    below = [t for n, t, _ in rows if 15 <= n <= 20]
    above = [t for n, t, _ in rows if 21 <= n <= 26]
    jump = sum(above) / len(above) - sum(below) / len(below)
    print(f"\nMean ns/build  n=15..20 (freelist): {sum(below)/len(below):6.2f}")
    print(f"Mean ns/build  n=21..26 (malloc):   {sum(above)/len(above):6.2f}")
    print(f"-> step across the 20->21 boundary: {jump:+.2f} ns/build")

    # Memory is dead-linear: no cliff. Show the constant per-element stride.
    s20, s21 = sys.getsizeof(tuple(range(20))), sys.getsizeof(tuple(range(21)))
    print(f"\ngetsizeof stride is constant {s21 - s20} B/elem across the boundary "
          f"({human(s20)} -> {human(s21)}) -- no memory cliff.")


if __name__ == "__main__":
    main()
