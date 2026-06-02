"""Chapter 5 - Exercise 1: deconstruct the for loop.

Task: rewrite `for i in obj: do_work(i)` using only iter(), next(), and
try/except StopIteration. Then show a generator IS its own iterator while a
list needs a separate list-iterator built on top.

Takeaway: for == iter() once, then next() until StopIteration. A list pays
twice: materialize the data, then wrap it in an iterator.

Run: .venv/bin/python chapter_5/ex01_for_deconstructed.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from perf import peak_bytes, time_s, human  # noqa: E402


def manual_for(obj, do_work):
    it = iter(obj)
    while True:
        try:
            i = next(it)
        except StopIteration:
            break
        do_work(i)


def gen(n):
    for i in range(n):
        yield i


def main():
    collected = []
    manual_for([10, 20, 30], collected.append)
    print("manual_for over list ->", collected)

    g = gen(3)
    print("generator is its own iterator? ", iter(g) is g)          # True
    print("type(g) == type(iter(g))?      ", type(g) == type(iter(g)))

    lst = [1, 2, 3]
    print("iter(list) is list?            ", iter(lst) is lst)      # False -- new object
    print("type(list) != type(iter(list))?", type(lst) != type(iter(lst)))

    # Time + memory: looping a prebuilt list vs a generator over N items.
    N = 1_000_000
    consume_list = lambda: sum(1 for _ in list(range(N)))   # builds the list first
    consume_gen = lambda: sum(1 for _ in gen(N))            # nothing materialized
    print(f"\nLoop over {N:,} items:")
    print(f"  prebuilt list: {time_s(consume_list, number=3) * 1e3:6.1f} ms   peak {human(peak_bytes(consume_list))}")
    print(f"  generator:     {time_s(consume_gen, number=3) * 1e3:6.1f} ms   peak {human(peak_bytes(consume_gen))}")
    print("  -> the list pays to allocate+store all N; the generator holds O(1) state")


if __name__ == "__main__":
    main()
