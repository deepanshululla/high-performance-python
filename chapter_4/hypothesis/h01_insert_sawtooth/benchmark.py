"""Chapter 4 - Hypothesis: dict inserts hide an O(n) resize "sawtooth".

Task: ex08 shows inserts are *amortized* flat (~38 ns each). That average hides
the truth: most inserts are O(1), but the rare insert that crosses 2/3-full
triggers a full rehash that copies every existing key -- an O(n) spike.

Hypothesis: timing each individual insert into a growing dict reveals a small
number of spikes, located exactly at the capacity-doubling boundaries (which we
confirm independently via sys.getsizeof), whose magnitude GROWS with dict size,
while the baseline insert stays ~flat. Average of all = the ex08 amortized cost.

Method: insert 0..N one at a time under perf_counter_ns; flag inserts far above
the median; cross-check against getsizeof jumps.

Run: .venv/bin/python chapter_4/hypothesis/h01_insert_sawtooth/benchmark.py
"""
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from perf import human  # noqa: E402

N = 1_000_000


def main():
    d = {}
    times = [0] * N
    resizes = []       # (insert #, time_ns, size_before, size_after) at each capacity jump
    prev_size = sys.getsizeof(d)
    pc = time.perf_counter_ns
    for i in range(N):
        t0 = pc()
        d[i] = i
        t1 = pc()
        times[i] = t1 - t0
        s = sys.getsizeof(d)
        if s != prev_size:
            resizes.append((i, t1 - t0, prev_size, s))
            prev_size = s

    srt = sorted(times)
    median = srt[len(srt) // 2]
    # Baseline = typical NON-resize insert (90th percentile excludes the spikes).
    resize_idx = {i for i, *_ in resizes}
    non_resize = [t for i, t in enumerate(times) if i not in resize_idx]
    p90 = sorted(non_resize)[int(len(non_resize) * 0.90)]

    print(f"Inserted {N:,} keys one at a time.\n")
    print(f"median insert:            {median:>6} ns")
    print(f"90th-pct non-resize:      {p90:>6} ns   (the flat baseline)")
    print(f"mean over ALL inserts:    {sum(times)/N:>9.1f} ns   (amortized -- compare ex08 ~38 ns)\n")
    print(f"The {len(resizes)} capacity-doubling resizes (deterministic getsizeof jumps):\n")
    print("   at insert #      insert time     capacity jump      x median")
    for i, t, before, after in resizes:
        print(f"  {i:>10,}   {t/1000:10.1f} us    {human(before):>8} -> {human(after):<8}  {t/median:7.0f}x")

    biggest = max(resizes, key=lambda r: r[1])
    print(f"\n-> every resize copies the whole table, so the spike GROWS with size:")
    print(f"   the last one ({biggest[0]:,} keys) took {biggest[1]/1000:.0f} us "
          f"= {biggest[1]/median:.0f}x a normal insert.")
    print("-> the cheap inserts between resizes keep the MEAN at the flat amortized")
    print("   cost ex08 reports. Amortization isn't 'no O(n)' -- it's 'rare O(n)'.")


if __name__ == "__main__":
    main()
