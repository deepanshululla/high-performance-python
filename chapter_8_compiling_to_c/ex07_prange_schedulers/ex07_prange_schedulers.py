"""Chapter 8 - Exercise 7: why OpenMP scheduling matters for uneven work.

Task: ex03 used `schedule="guided"` without justifying it. Here we compile the same
Cython+OpenMP Julia loop three times -- `static`, `dynamic`, `guided` -- and time each on
the identical grid, so the chapter's scheduling discussion becomes a measurement.

Takeaway: the Julia workload is wildly uneven (some pixels escape in one step, some run
the full 300 iterations). `static` splits the grid into equal contiguous blocks up front,
so whichever thread lands on the dense interior of the fractal runs long while the others
finish early and sit idle -- the slowest thread sets the wall-clock. `dynamic` and
`guided` hand out work at runtime, keeping every core busy through the long tail. The win
isn't from doing less work; it's from wasting fewer idle core-seconds.

Builds on first run via setup.py (same libomp auto-discovery as ex03).

Run: .venv/bin/python chapter_8_compiling_to_c/ex07_prange_schedulers/ex07_prange_schedulers.py
"""
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))   # repo root -> perf.py
sys.path.insert(0, str(HERE.parents[1]))   # chapter dir -> _julia.py
sys.path.insert(0, str(HERE.parent))       # this folder -> compiled module

from perf import time_s  # noqa: E402
import _julia  # noqa: E402


def ensure_built():
    if list(HERE.parent.glob("_cyjulia_sched*.so")):
        return
    print("Building _cyjulia_sched (Cython + OpenMP, 3 schedules) ... first run only\n")
    subprocess.run([sys.executable, "setup.py", "build_ext", "--inplace"],
                   cwd=HERE.parent, check=True)


def main():
    ensure_built()
    import _cyjulia_sched  # noqa: E402

    zs, cs = _julia.build_inputs_numpy()
    checksum = _julia.expected_checksum()
    maxiter = _julia.DEFAULT_MAXITER
    cores = os.cpu_count() or 1
    print(f"Julia grid: {len(zs):,} pixels, maxiter={maxiter}  ({cores} cores)\n")

    scheds = [("static ", _cyjulia_sched.static),
              ("dynamic", _cyjulia_sched.dynamic),
              ("guided ", _cyjulia_sched.guided)]
    for name, fn in scheds:
        assert int(fn(maxiter, zs, cs).sum()) == checksum, name
    print(f"All schedules match sum(output) == {checksum:,}\n")

    print("Cython + OpenMP, one 1000x1000 grid (best of 7):")
    times = {}
    for name, fn in scheds:
        t = time_s(lambda fn=fn: fn(maxiter, zs, cs), number=1, repeat=7)
        times[name.strip()] = t
        print(f"  schedule={name} : {t * 1000:6.1f} ms")

    best = min(times, key=lambda k: times[k])
    print(f"\n  fastest: {best}.  static is {times['static'] / times[best]:.2f}x the best "
          f"-- its equal up-front split strands a thread on the dense interior.")
    print("  dynamic/guided rebalance at runtime, so the slowest thread finishes sooner.")


if __name__ == "__main__":
    main()
