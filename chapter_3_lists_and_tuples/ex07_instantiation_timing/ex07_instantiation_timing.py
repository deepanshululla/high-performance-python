"""Chapter 3 - Exercise 7: list vs tuple instantiation cost (Example 3-9).

Task: confirm a tuple literal is several times faster to create than a list
literal. Then check what happens past the freelist size limit (sizes 0-20).

Takeaway: an immutable tuple of size <= 20 is pulled off CPython's freelist
(no kernel round-trip to reserve memory); a fresh list must allocate. Beyond
size 20 there is no tuple freelist, so the gap narrows.

Run: .venv/bin/python chapter_3/ex07_instantiation_timing/ex07_instantiation_timing.py
"""
import sys
import timeit

N = 10_000_000


def main():
    t_list = timeit.timeit("[0,1,2,3,4,5,6,7,8,9]", number=N) / N * 1e9
    t_tuple = timeit.timeit("(0,1,2,3,4,5,6,7,8,9)", number=N) / N * 1e9
    print(f"list  literal (size 10): {t_list:6.2f} ns/op")
    print(f"tuple literal (size 10): {t_tuple:6.2f} ns/op")
    print(f"-> tuple is {t_list / t_tuple:0.1f}x faster (freelist, no syscall)\n")

    # Past the freelist (size > 20): build from range so the literal isn't folded.
    big_list = timeit.timeit("list(r)", setup="r=range(30)", number=N) / N * 1e9
    big_tuple = timeit.timeit("tuple(r)", setup="r=range(30)", number=N) / N * 1e9
    print(f"list(range(30)):  {big_list:6.2f} ns/op")
    print(f"tuple(range(30)): {big_tuple:6.2f} ns/op  (size>20: no freelist, gap narrows)")

    # Memory: a tuple is also smaller (no over-allocation, no resize bookkeeping).
    lst = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    tpl = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)
    print(f"\nMemory (size-10 container): list {sys.getsizeof(lst)} B  vs  tuple {sys.getsizeof(tpl)} B")
    print(f"  -> tuple saves {sys.getsizeof(lst) - sys.getsizeof(tpl)} B per object (compounds across millions)")


if __name__ == "__main__":
    main()
