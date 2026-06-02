"""Chapter 5 - Exercise 3: the len([...]) trap.

Task: counting Fibonacci numbers divisible by 3 via len([... ]) materializes a
list just to measure and discard it. Rewrite with sum(1 for ...) for O(1) memory.

Takeaway: a list comprehension re-materializes every match; a generator
expression folds one value at a time. The only syntactic difference is [] vs ().

Run (time):   .venv/bin/python chapter_5/ex03_len_trap.py
Run (memory): .venv/bin/python -m memory_profiler chapter_5/ex03_len_trap.py
"""
import builtins
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from perf import peak_bytes, time_s, human  # noqa: E402

# `profile` is injected by memory_profiler; no-op otherwise.
profile = getattr(builtins, "profile", lambda fn: fn)


def fibonacci_gen(num_items):
    a, b = 0, 1
    while num_items:
        yield a
        a, b = b, a + b
        num_items -= 1


@profile
def count_with_list():
    return len([n for n in fibonacci_gen(100_000) if n % 3 == 0])  # wasteful


@profile
def count_with_gen():
    return sum(1 for n in fibonacci_gen(100_000) if n % 3 == 0)    # O(1) memory


def main():
    a, b = count_with_list(), count_with_gen()
    print(f"len([...])         -> {a}")
    print(f"sum(1 for ...)     -> {b}   (same answer)")
    assert a == b

    t_list = time_s(count_with_list, number=1, repeat=3)
    t_gen = time_s(count_with_gen, number=1, repeat=3)
    print("\nTime:")
    print(f"  len([...]):     {t_list * 1e3:6.1f} ms")
    print(f"  sum(1 for ...): {t_gen * 1e3:6.1f} ms")

    print("\nMemory (tracemalloc peak):")
    print(f"  len([...]):     {human(peak_bytes(count_with_list)):>9}  (materializes the matches)")
    print(f"  sum(1 for ...): {human(peak_bytes(count_with_gen)):>9}  (folds one value at a time)")
    print("  -> only difference in code is [] vs () -- huge difference in memory")
    print("\n(RSS view: .venv/bin/python -m memory_profiler chapter_5/ex03_len_trap.py)")


if __name__ == "__main__":
    main()
    count_with_list()
    count_with_gen()
