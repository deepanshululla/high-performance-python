"""ex05 — the queue as a buffer: absorbing a burst without dropping work.

The book's motivating story for a queue is a traffic spike. When a user rates an
item, the site wants to recompute recommendations; without a queue, the "rate"
action calls the recommendation service *directly*, and if thousands of users
rate things at once the recommendation servers are swamped, time out, and start
dropping work. With a queue in between, the "rate" action just drops a message
and returns instantly; the recommendation servers pull work *when they are ready*,
and the queue swells to hold the backlog until they catch up. The producer never
blocks, and nothing is dropped.

This exercise makes that buffering visible. We send the same number of jobs to a
Redis queue drained by a fixed set of consumers, under two arrival patterns:

  * **burst** — all the jobs arrive at once (the spike), and
  * **steady** — the jobs arrive paced to match the consumers' service rate.

We sample the queue depth (the Redis list length) over time for each. The burst
makes the queue balloon and then drain; the steady stream keeps it near empty.
The finding we are after is what *stays the same*: the time to finish all the work
is set by the consumers, not by how bursty the arrivals were — the queue converts
a spike in arrivals into a spike in queue depth, not a spike in completion time or
a pile of dropped work.
"""
import multiprocessing as mp
import pathlib
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[0]))

from _cluster import estimate_pi_block, get_redis, ephemeral_redis  # noqa: E402

CTX = mp.get_context("fork")
JOBS_KEY = "hpp:ch11:ex05:jobs"
DONE_KEY = "hpp:ch11:ex05:done"
STOP = b"STOP"
DARTS_PER_JOB = 500_000            # ~0.05 s of work per job
N_JOBS = 160
N_CONSUMERS = 4
SAMPLE_DT = 0.02                   # how often to sample queue depth


def consumer_loop():
    """Drain jobs until STOP, counting each via an atomic Redis INCR."""
    r = get_redis()
    while True:
        item = r.blpop(JOBS_KEY, timeout=10)
        if item is None:
            break
        _key, value = item
        if value == STOP:
            break
        estimate_pi_block(int(value))
        r.incr(DONE_KEY)            # INCR is atomic — no lost updates across consumers


def run_scenario(arrival, service_interval):
    r = get_redis()
    r.delete(JOBS_KEY)
    r.set(DONE_KEY, 0)

    procs = [CTX.Process(target=consumer_loop) for _ in range(N_CONSUMERS)]
    for p in procs:
        p.start()

    samples = []
    stop_sampling = threading.Event()
    t0 = time.perf_counter()

    def sampler():
        while not stop_sampling.is_set():
            samples.append((time.perf_counter() - t0, r.llen(JOBS_KEY)))
            time.sleep(SAMPLE_DT)

    def producer():
        rp = get_redis()
        for _ in range(N_JOBS):
            rp.rpush(JOBS_KEY, DARTS_PER_JOB)
            if arrival == "steady":
                time.sleep(service_interval)
        for _ in range(N_CONSUMERS):
            rp.rpush(JOBS_KEY, STOP)

    sth = threading.Thread(target=sampler); sth.start()
    pth = threading.Thread(target=producer); pth.start()
    pth.join()
    for p in procs:
        p.join()
    total = time.perf_counter() - t0
    stop_sampling.set(); sth.join()

    done = int(r.get(DONE_KEY))
    assert done == N_JOBS, f"{arrival}: consumers processed {done} != {N_JOBS} jobs"
    peak = max(d for _t, d in samples)
    return {"samples": samples, "total": total, "peak": peak}


def measure():
    # Pace the steady arrivals to match the consumers' service rate: one job every
    # (job_time / consumers) seconds keeps arrival ≈ consumption.
    job_time = DARTS_PER_JOB / 10_000_000      # ~darts/sec measured for this loop
    service_interval = job_time / N_CONSUMERS
    with ephemeral_redis() as r:
        if r is None:
            return None
        return {
            "burst": run_scenario("burst", service_interval),
            "steady": run_scenario("steady", service_interval),
        }


def main():
    r = measure()
    if r is None:
        print("[skipped] no Redis reachable and Docker unavailable — cannot run an "
              "ephemeral broker.")
        return
    print(f"queue-as-buffer: {N_JOBS} jobs of {DARTS_PER_JOB:,} darts, {N_CONSUMERS} consumers")
    for name in ("burst", "steady"):
        s = r[name]
        print(f"  {name:>6} arrival : finished in {s['total']:5.2f} s, "
              f"peak queue depth {s['peak']:3d} jobs")
    print(f"  completion time barely moves ({r['burst']['total']:.2f}s vs "
          f"{r['steady']['total']:.2f}s) while peak depth differs "
          f"{r['burst']['peak']} vs {r['steady']['peak']} — "
          "the queue absorbs the spike, the consumers set the pace")


if __name__ == "__main__":
    main()
