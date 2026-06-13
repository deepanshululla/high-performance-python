"""Chapter 3 - Hypothesis: `x in list` time is linear in x's position.

Task: ex02 frames list.index as an O(n) linear scan. Membership (`in`) is the
same scan. Prove it by varying *where* the target sits.

Hypothesis: for a list of N ints, `target in data` costs:
  - front (target=0):     ~O(1)  -- found on the first compare
  - middle (target=N/2):  ~O(N/2)
  - end (target=N-1):     ~O(N)
  - absent (target=-1):   ~O(N)  -- worst case, scans every element
and the end/absent times scale linearly with N.

Run: .venv/bin/python chapter_3/hypothesis/h03_membership_position/benchmark.py
"""
import timeit


def time_in(data, target, number):
    return timeit.timeit("target in data", globals={"data": data, "target": target},
                         number=number) / number * 1e6  # microseconds/op


def main():
    print("Time for `target in list` by target position (us/op):\n")
    print("      N        front       middle         end       absent")
    for N in (1_000, 100_000, 1_000_000):
        data = list(range(N))
        number = max(10, 5_000_000 // N)
        front = time_in(data, 0, number * 50)        # cheap: more reps for stability
        middle = time_in(data, N // 2, number)
        end = time_in(data, N - 1, number)
        absent = time_in(data, -1, number)
        print(f"  {N:>9,}  {front:9.4f}    {middle:9.3f}    {end:9.3f}    {absent:9.3f}")

    print("\n-> front stays flat (~O(1)); middle ~ end/2; end ~ absent (full scan).")
    print("-> end/absent times grow ~10x when N grows 10x: the scan is O(n).")


if __name__ == "__main__":
    main()
