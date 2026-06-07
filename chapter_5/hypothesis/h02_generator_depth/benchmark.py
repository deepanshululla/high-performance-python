"""Chapter 5 - Hypothesis: deep generator pipelines cost CPU linearly in depth.

Task: ex06 celebrates lazy pipelines as flat in *memory*. The counterpoint: each
stacked generator is a Python frame that must be resumed once per item, so a deep
chain is NOT free on the CPU axis.

Hypothesis: stacking K identity generators over the same stream makes per-item
pull time grow ~linearly in K (each added layer adds a near-constant per-item
cost). Memory stays flat -- the trade is CPU, not RAM.

Method: wrap an int stream in K `identity` generators and time consuming it.

Run: .venv/bin/python chapter_5/hypothesis/h02_generator_depth/benchmark.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from perf import time_s, peak_bytes, human  # noqa: E402

N = 500_000


def identity(it):
    for x in it:
        yield x


def stacked(K, n):
    it = iter(range(n))
    for _ in range(K):
        it = identity(it)
    return it


def main():
    print(f"Per-item pull time vs pipeline depth (consuming {N:,} ints):\n")
    print("   depth K    total       ns/item    ns/item/layer    peak mem")
    base = 0.0
    for K in (0, 1, 2, 5, 10, 20, 50):
        t = time_s(lambda: sum(stacked(K, N)), number=1, repeat=5)
        peak = peak_bytes(lambda: sum(stacked(K, N)))
        per_item = t / N * 1e9
        if K == 0:
            base = per_item
            per_layer = ""
        else:
            per_layer = f"{(per_item - base) / K:8.2f}"
        print(f"  {K:>7}   {t*1e3:7.1f} ms   {per_item:8.1f}   {per_layer:>12}     {human(peak)}")

    print("\n-> ns/item rises ~linearly with K (constant cost per added layer), while")
    print("   peak memory stays flat: lazy is O(1) in RAM but O(depth) per item in CPU.")


if __name__ == "__main__":
    main()
