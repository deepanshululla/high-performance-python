"""Chapter 5 - Exercise 2: Fibonacci list vs generator (time + memory).

Task: implement both, then measure time (here) and memory (via memory_profiler).

Takeaway: the generator keeps only the current `a, b` -> O(1) memory regardless
of num_items, and is faster (no appends, no overallocation/copy, no big array).

Run (time):   .venv/bin/python chapter_5/ex02_fib_list_vs_gen/ex02_fib_list_vs_gen.py
Run (memory): .venv/bin/python -m memory_profiler chapter_5/ex02_fib_list_vs_gen/ex02_fib_list_vs_gen.py
              (the @profile decorators below activate under memory_profiler)
"""
import builtins
import pathlib
import sys
import timeit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from perf import peak_bytes, human  # noqa: E402

# memory_profiler injects `profile` into builtins when run via `-m memory_profiler`;
# fall back to a no-op decorator otherwise.
profile = getattr(builtins, "profile", lambda fn: fn)


def fibonacci_list(num_items):
    numbers, a, b = [], 0, 1
    while len(numbers) < num_items:
        numbers.append(a)
        a, b = b, a + b
    return numbers


def fibonacci_gen(num_items):
    a, b = 0, 1
    while num_items:
        yield a
        a, b = b, a + b
        num_items -= 1


@profile
def consume_list():
    for _ in fibonacci_list(100_000):
        pass


@profile
def consume_gen():
    for _ in fibonacci_gen(100_000):
        pass


def main():
    t_list = min(timeit.repeat(consume_list, repeat=3, number=1))
    t_gen = min(timeit.repeat(consume_gen, repeat=3, number=1))
    print("Time (consume 100,000 Fibonacci numbers):")
    print(f"  fibonacci_list: {t_list * 1e3:7.1f} ms")
    print(f"  fibonacci_gen:  {t_gen * 1e3:7.1f} ms   ({t_list / t_gen:0.1f}x faster)")

    # Memory (tracemalloc peak, self-contained -- no external profiler needed):
    m_list = peak_bytes(consume_list)
    m_gen = peak_bytes(consume_gen)
    print("\nMemory (peak allocated while consuming):")
    print(f"  fibonacci_list: {human(m_list):>10}   (stores all 100,000 big ints)")
    print(f"  fibonacci_gen:  {human(m_gen):>10}   (holds only a, b -> O(1) state)")
    print(f"  -> list uses ~{m_list / max(m_gen, 1):,.0f}x the memory of the generator")
    print("\n(For RSS-based numbers: .venv/bin/python -m memory_profiler chapter_5/ex02_fib_list_vs_gen/ex02_fib_list_vs_gen.py)")


if __name__ == "__main__":
    main()
    # Under memory_profiler these print the per-line memory report:
    consume_list()
    consume_gen()
