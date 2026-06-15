"""ex06 — when a Queue makes parallelism *slower* than a single process.

A `multiprocessing.Queue` lets producers and consumers pass arbitrary pickled
objects between processes. That flexibility is not free: every item is pickled,
shipped, and unpickled, with locking around the queue. When the per-item work is
tiny — like a primality check that mostly hits even numbers and bails in one step
— the pickling cost dwarfs the computation, and adding workers makes things
worse, not better.

We reproduce the book's deliberately damning result. Worker processes block on
`possible_primes_queue.get()`, check each candidate, and `put` confirmed primes
on a results queue; the parent feeds the candidates followed by one poison pill
per worker (a sentinel that tells a worker to shut down). We run it with 1, 2, 4
and 8 workers and compare against a plain single-process loop with no queue at
all — which wins every time, because here the communication *is* the workload.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[0]))

from perf import time_s  # noqa: E402
from _primes import check_prime  # noqa: E402
from _mp import CTX  # noqa: E402

LO, HI = 1_000_000, 1_150_000          # 150,000 candidates — light per-item work
NUMBERS = range(LO, HI)
EXPECTED_PRIMES = 10804                  # correctness anchor (verified once)
FLAG_ALL_DONE = "WORK_FINISHED"
FLAG_WORKER_DONE = "WORKER_FINISHED"
WORKER_COUNTS = [1, 2, 4, 8]


def worker(possible_primes_queue, definite_primes_queue):
    """Consume candidates until the poison pill; post confirmed primes back."""
    while True:
        n = possible_primes_queue.get()
        if n == FLAG_ALL_DONE:
            definite_primes_queue.put(FLAG_WORKER_DONE)
            break
        if check_prime(n):
            definite_primes_queue.put(n)


def run_queue(nbr_workers):
    # Plain multiprocessing.Queue (a fast pipe + lock), passed straight to the
    # workers. A manager.Queue would be far slower still — every operation there
    # is an RPC to a separate manager process — but a plain Queue already loses.
    possible_primes_queue = CTX.Queue()
    definite_primes_queue = CTX.Queue()

    procs = [CTX.Process(target=worker,
                         args=(possible_primes_queue, definite_primes_queue))
             for _ in range(nbr_workers)]
    for p in procs:
        p.start()

    for n in NUMBERS:
        possible_primes_queue.put(n)
    for _ in range(nbr_workers):
        possible_primes_queue.put(FLAG_ALL_DONE)

    primes = []
    finished = 0
    while True:
        result = definite_primes_queue.get()
        if result == FLAG_WORKER_DONE:
            finished += 1
            if finished == nbr_workers:
                break
        else:
            primes.append(result)
    for p in procs:
        p.join()
    assert len(primes) == EXPECTED_PRIMES, f"got {len(primes)} primes"
    return len(primes)


def run_serial_noqueue():
    primes = [n for n in NUMBERS if check_prime(n)]
    assert len(primes) == EXPECTED_PRIMES
    return len(primes)


def measure():
    """Return (serial_seconds, [(workers, seconds)...])."""
    serial = time_s(run_serial_noqueue, number=1, repeat=1)
    rows = [(w, time_s(lambda w=w: run_queue(w), number=1, repeat=1))
            for w in WORKER_COUNTS]
    return serial, rows


def main():
    serial, rows = measure()
    print(f"prime check over {HI - LO:,} candidates")
    print(f"  serial, no queue : {serial:.2f}s  (1.00x)  <- the one to beat")
    for w, t in rows:
        verdict = "slower!" if t > serial else "faster"
        print(f"  {w} worker queue   : {t:.2f}s  ({serial / t:.2f}x)  {verdict}")


if __name__ == "__main__":
    main()
