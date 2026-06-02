"""Chapter 3 - Exercise 5: reverse-engineer list overallocation.

Task:
  1. Predict capacity M with CPython's growth formula M = (N + (N>>3) + 6) & ~3.
  2. Detect real capacity jumps by watching sys.getsizeof while appending.
  3. Show overallocation fires only on append: list(range(n)) is tighter than
     the same list grown by appends.

Takeaway: lists trade memory for time. Geometric overallocation makes append
amortized O(1), but that headroom is dead weight -- worst for tiny lists
(1 item -> 4 slots, 9 -> 16). Casting a comprehension back through list()
reclaims it.

Run: .venv/bin/python chapter_3/ex05_overallocation.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from perf import peak_bytes, time_s, human  # noqa: E402


def predict_M(N):
    return (N + (N >> 3) + 6) & ~3


def capacity_from_size(nbytes):
    # 64-bit CPython: header + 8 bytes per pointer slot.
    header = sys.getsizeof([])
    return (nbytes - header) // 8


def main():
    print("Predicted capacity M from the growth formula:")
    for N in (1, 2, 9, 100, 1_000, 1_000_000):
        print(f"  N={N:>9,}  ->  M={predict_M(N):>9,}")

    print("\nObserved realloc boundaries while appending (len, getsizeof, capacity):")
    prev = None
    l = []
    for i in range(40):
        l.append(i)
        s = sys.getsizeof(l)
        if s != prev:
            print(f"  len={len(l):>3}  size={s:>4}B  capacity~={capacity_from_size(s):>3}")
            prev = s

    print("\nappend-grown vs list()-built (same 1,000 ints):")
    grown = []
    for i in range(1_000):
        grown.append(i)
    built = list(range(1_000))
    print(f"  grown by append: {sys.getsizeof(grown):>6} B")
    print(f"  list(range(..)): {sys.getsizeof(built):>6} B  <- no append headroom")

    # Time + memory of building 1,000,000 ints two ways.
    def build_append():
        out = []
        for i in range(1_000_000):
            out.append(i)
        return out

    t_app = time_s(build_append, number=1, repeat=3)
    t_list = time_s(lambda: list(range(1_000_000)), number=1, repeat=3)
    print("\nBuild 1,000,000 ints:")
    print(f"  append loop:     {t_app * 1e3:7.1f} ms   peak {human(peak_bytes(build_append))}")
    print(f"  list(range(..)): {t_list * 1e3:7.1f} ms   peak {human(peak_bytes(lambda: list(range(1_000_000))))}")
    print(f"  -> list() is ~{t_app / t_list:.0f}x faster: no repeated resize+copy, exact allocation")


if __name__ == "__main__":
    main()
