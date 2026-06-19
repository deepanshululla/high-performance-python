"""ex04 — a Redis work queue, and scaling it by adding consumers.

This is the book's Queue topology made concrete (Figure 11-1). A producer drops
jobs onto a queue; a pool of consumers pulls them off and processes them. The
whole appeal of the design is the line the book draws under it: *"we can simply
scale horizontally by adding more data consumers until the message production
rate and the consumption rate are equal."* This exercise tests that claim by
measuring throughput as the consumer count grows from one to eight.

The queue is a Redis list. The producer `RPUSH`es a batch of jobs (each job is a
dart count — a chunk of the Chapter 11 pi workload, ~0.1 s of real CPU work) and
then one `STOP` sentinel per consumer. Each consumer is a separate process that
`BLPOP`s jobs off the list, computes, and counts what it did, shutting down when
it pulls its `STOP`. Because consumers are separate processes with their own GIL,
this is genuine parallelism — the queue is just how they find their next piece of
work.

Correctness anchor: across all consumers, exactly the jobs we enqueued must be
processed — no job lost, none done twice. We assert the total count equals the
batch size, so a queue bug that drops or duplicates work fails loudly.
"""
import multiprocessing as mp
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[0]))

from _cluster import estimate_pi_block, get_redis, ephemeral_redis, REDIS_URL  # noqa: E402

CTX = mp.get_context("fork")
JOBS_KEY = "hpp:ch11:ex04:jobs"
STOP = b"STOP"
DARTS_PER_JOB = 1_000_000          # ~0.1 s of pure-Python work per job
N_JOBS = 64
CONSUMER_COUNTS = [1, 2, 4, 8]


def consumer(_worker_id):
    """Pull jobs off the Redis list until a STOP sentinel; return jobs done.

    Opens its *own* Redis connection — a socket must never be shared across a
    fork, so each worker process connects independently on first use.
    """
    r = get_redis()
    done = 0
    while True:
        item = r.blpop(JOBS_KEY, timeout=10)
        if item is None:
            break                      # queue drained and no sentinel — safety net
        _key, value = item
        if value == STOP:
            break
        estimate_pi_block(int(value))
        done += 1
    return done


def fill_queue(r, n_consumers):
    """Load the queue with N_JOBS jobs followed by one STOP per consumer."""
    r.delete(JOBS_KEY)
    pipe = r.pipeline()
    for _ in range(N_JOBS):
        pipe.rpush(JOBS_KEY, DARTS_PER_JOB)
    for _ in range(n_consumers):
        pipe.rpush(JOBS_KEY, STOP)
    pipe.execute()


def measure():
    with ephemeral_redis() as r:
        if r is None:
            return None
        rows = []
        for m in CONSUMER_COUNTS:
            fill_queue(r, m)
            with CTX.Pool(m) as pool:
                t0 = time.perf_counter()
                counts = pool.map(consumer, range(m))
                dt = time.perf_counter() - t0
            assert sum(counts) == N_JOBS, f"{m} consumers processed {sum(counts)} != {N_JOBS} jobs"
            rows.append((m, dt))
        return rows


def main():
    rows = measure()
    if rows is None:
        print("[skipped] no Redis reachable and Docker unavailable — cannot run an "
              "ephemeral broker.")
        return
    base = rows[0][1]
    print(f"Redis work queue: drain {N_JOBS} jobs of {DARTS_PER_JOB:,} darts each")
    print(f"  (queue: a Redis list at {REDIS_URL}, key {JOBS_KEY!r})")
    print(f"  {'consumers':>9}  {'time':>7}  {'jobs/s':>8}  {'speedup':>8}")
    for m, dt in rows:
        print(f"  {m:>9}  {dt:6.2f}s  {N_JOBS/dt:8.1f}  {base/dt:7.2f}x")
    best = max(base / dt for _, dt in rows)
    print(f"  peak speedup {best:.1f}x — add consumers and throughput rises until the cores run out")


if __name__ == "__main__":
    main()
