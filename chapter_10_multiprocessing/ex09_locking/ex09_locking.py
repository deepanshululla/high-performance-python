"""ex09 — why a shared counter needs a lock (and what the lock costs).

Four processes each increment a shared integer N times. The correct final value
is 4*N. The catch is that `value.value += 1` is not atomic: it reads the current
value, adds one, and writes it back as three separate steps. When two processes
interleave those steps, both read the same starting number and both write the
same result, so one increment is silently lost. The counter ends up *low* — never
corrupt, just wrong.

We run three variants:

  Value, no lock      — races; final count is short by a margin that grows with N
  Value + Lock        — every increment wrapped in `with lock`; correct, but slower
  RawValue + Lock     — same lock, but the value itself carries no internal lock of
                        its own, shaving the redundant second lock off each step

The book notes that on a fast modern machine with 3.12 the race is hard to trigger
at 4,000 but reliable at 40,000 — the bigger the count, the wider the window for a
collision. We count high enough to make the loss show every run.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[0]))

from perf import time_s  # noqa: E402
from _mp import CTX  # noqa: E402

NBR_PROCESSES = 4
MAX_COUNT_PER_PROCESS = 100_000
EXPECTED = NBR_PROCESSES * MAX_COUNT_PER_PROCESS


def _work_nolock(value, max_count):
    for _ in range(max_count):
        value.value += 1


def _work_lock(value, max_count, lock):
    for _ in range(max_count):
        with lock:
            value.value += 1


def _run(work, use_lock, raw):
    value = CTX.RawValue("i", 0) if raw else CTX.Value("i", 0)
    lock = CTX.Lock()
    args_extra = (lock,) if use_lock else ()
    procs = [CTX.Process(target=work, args=(value, MAX_COUNT_PER_PROCESS, *args_extra))
             for _ in range(NBR_PROCESSES)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    return value.value


def run_nolock():
    return _run(_work_nolock, use_lock=False, raw=False)


def run_value_lock():
    return _run(_work_lock, use_lock=True, raw=False)


def run_rawvalue_lock():
    return _run(_work_lock, use_lock=True, raw=True)


def measure():
    """Return {variant: (final_count, seconds)} for the three approaches."""
    out = {}
    holder = {}
    for name, fn in (("Value, no lock", run_nolock),
                     ("Value + Lock", run_value_lock),
                     ("RawValue + Lock", run_rawvalue_lock)):
        t = time_s(lambda fn=fn, name=name: holder.__setitem__(name, fn()),
                   number=1, repeat=3)
        out[name] = (holder[name], t)
    return out


def main():
    out = measure()
    print(f"{NBR_PROCESSES} processes each counting to {MAX_COUNT_PER_PROCESS:,} "
          f"(expected {EXPECTED:,})")
    for name, (count, t) in out.items():
        lost = EXPECTED - count
        tag = "CORRECT" if lost == 0 else f"LOST {lost:,} ({100 * lost / EXPECTED:.0f}%)"
        print(f"  {name:<16}: {count:>8,}  {tag:<20} {t * 1000:6.1f}ms")


if __name__ == "__main__":
    main()
