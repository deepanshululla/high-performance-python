"""Chapter 4 - Hypothesis: lookup time degrades smoothly as hash entropy drops.

Task: ex06 only tests the two endpoints -- a perfect hash (O(1)) vs a constant
hash returning 42 (O(n)). Reality is a spectrum. Fill in the curve.

Hypothesis: take real string hashes but mask them down to `b` usable bits
(b = number of distinct buckets is ~2**b). As b shrinks, keys crowd into fewer
buckets, probe chains lengthen, and average set-membership time rises smoothly
from ~O(1) toward the all-collide O(n) case -- not a step, a curve.

Method: build a set of N keys whose __hash__ is `real_hash & ((1<<b)-1)`, then
time average membership over all N keys for each b.

Run: .venv/bin/python chapter_4/hypothesis/h02_collision_entropy_curve/benchmark.py
"""
import timeit

N = 4_000


def make_masked_class(bits):
    mask = (1 << bits) - 1

    class Masked(str):
        __slots__ = ()

        def __hash__(self):
            return str.__hash__(self) & mask

    Masked.__name__ = f"Masked{bits}"
    return Masked


def main():
    keys = [f"key-{i:06d}" for i in range(N)]
    print(f"Average set membership over {N:,} keys, as hash entropy shrinks:\n")
    print("  bits   distinct buckets   ns/lookup    vs 64-bit")
    base = None
    for bits in (64, 20, 16, 12, 10, 8, 6, 4, 2, 1, 0):
        Cls = make_masked_class(bits)
        items = [Cls(k) for k in keys]
        s = set(items)
        distinct = len({hash(x) for x in items})
        number = 3 if bits <= 6 else 30   # low-entropy lookups are slow; fewer reps
        t = timeit.timeit("for k in items: k in s",
                          globals={"items": items, "s": s}, number=number)
        ns = t / number / N * 1e9
        if base is None:
            base = ns
        print(f"  {bits:>4}   {distinct:>16,}   {ns:9.1f}   {ns/base:7.1f}x")

    print("\n-> with full entropy every key has its own bucket (~O(1)); as bits")
    print("   fall the buckets collapse and the average walk grows smoothly toward")
    print("   the O(n) all-collide case ex06 measured at the extreme.")


if __name__ == "__main__":
    main()
