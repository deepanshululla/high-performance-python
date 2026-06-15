"""h01 — fork vs spawn: the start method the book assumes vs the one macOS gives you.

HYPOTHESIS
  The book was written on Linux, where multiprocessing defaults to *fork*. On
  macOS with CPython 3.14 the default is *spawn*. We predict two consequences,
  both verifiable here:

    (A) spawn is measurably slower to start a pool, because each worker is a
        brand-new interpreter that must re-import everything, where fork just
        clones the parent.
    (B) the book's "share state through a module global" trick (ex07's flags,
        ex08's shared array) silently BREAKS under spawn: a forked child inherits
        the parent's post-import mutations, a spawned child re-imports the module
        and sees only its import-time defaults.

  PREDICTION: both confirmed — fork starts faster, and only fork inherits the
  mutated global. VERDICT decided by the measured data below.

WHY IT MATTERS
  Every Chapter 10 exercise that shares state forces a fork context (see _mp.py)
  precisely because of (B). This lab is where we show what would happen if we
  hadn't — and what the convenience costs in (A).
"""
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))   # repo root (perf/vizutil if needed)

import multiprocessing as mp  # noqa: E402

# A module-level global with an import-time default. The parent will mutate it to
# 42 *after* import; whether a child sees 42 or 0 reveals its start method's
# inheritance behaviour.
SHARED_FLAG = {"value": 0}
DEFAULT_START_METHOD = mp.get_start_method()
METHODS = ["fork", "spawn"]


def _read_shared(q):
    """Worker: report what this child process sees in the inherited global."""
    q.put(SHARED_FLAG["value"])


def _trivial(x):
    return x * x


def measure_startup(method, workers=8, repeat=5):
    """Best-of-N seconds to spin up a Pool of `workers` and run one tiny map."""
    ctx = mp.get_context(method)
    best = float("inf")
    for _ in range(repeat):
        t0 = time.time()
        with ctx.Pool(workers) as pool:
            pool.map(_trivial, range(workers))
        best = min(best, time.time() - t0)
    return best


def measure_inheritance(method):
    """Return what a child sees in SHARED_FLAG after the parent sets it to 42.

    fork -> 42 (inherited); spawn -> 0 (re-imported default, mutation lost).
    """
    ctx = mp.get_context(method)
    SHARED_FLAG["value"] = 42
    q = ctx.Queue()
    p = ctx.Process(target=_read_shared, args=(q,))
    p.start()
    seen = q.get()
    p.join()
    SHARED_FLAG["value"] = 0
    return seen


def run():
    """Return the full result dict both the chart and the verdict read from."""
    startup = {m: measure_startup(m) for m in METHODS}
    inherit = {m: measure_inheritance(m) for m in METHODS}
    faster_ratio = startup["spawn"] / startup["fork"]
    a_confirmed = startup["spawn"] > startup["fork"]
    b_confirmed = inherit["fork"] == 42 and inherit["spawn"] == 0
    return {
        "default_method": DEFAULT_START_METHOD,
        "startup": startup,
        "inherit": inherit,
        "spawn_over_fork": faster_ratio,
        "A_confirmed": a_confirmed,
        "B_confirmed": b_confirmed,
        "verdict": "CONFIRMED" if (a_confirmed and b_confirmed) else "OVERTURNED",
    }


def main():
    r = run()
    print(f"default start method on this machine: {r['default_method']}")
    print()
    print("(A) pool startup cost (best of 5, 8 workers):")
    for m in METHODS:
        print(f"    {m:<6}: {r['startup'][m] * 1000:7.1f} ms")
    print(f"    -> spawn is {r['spawn_over_fork']:.1f}x slower to start  "
          f"[{'CONFIRMED' if r['A_confirmed'] else 'no'}]")
    print()
    print("(B) does a child inherit the parent's mutated global (set to 42)?")
    for m in METHODS:
        tag = "inherited" if r["inherit"][m] == 42 else "LOST (re-imported default)"
        print(f"    {m:<6}: child sees {r['inherit'][m]:>2}  -> {tag}")
    print(f"    -> only fork inherits  [{'CONFIRMED' if r['B_confirmed'] else 'no'}]")
    print()
    print(f"VERDICT: {r['verdict']} — the book assumes fork; macOS defaults to spawn, "
          f"which is slower to start AND breaks global-state sharing.")


if __name__ == "__main__":
    main()
