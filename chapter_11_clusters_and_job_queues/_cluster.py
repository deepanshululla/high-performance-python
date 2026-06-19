"""Shared workload and Redis plumbing for Chapter 11.

Chapter 11 is the book's most *operational* chapter — it is about clusters,
queues, and message brokers rather than a single tight inner loop. To keep the
study repo's promise that every number is measured, we anchor the abstract
topology lessons to two concrete, runnable things:

* A **shared CPU job** — one "unit of work" that a cluster engine, a queue
  consumer, or a Docker container all run identically, so the numbers across
  exercises are comparable. We reuse the book's own Monte Carlo pi estimator
  (Example 11-4) as that unit: throw darts at the unit square and count how many
  land inside the quarter circle. It is embarrassingly parallel, perfectly even
  when you want a clean signal, and trivially made *uneven* (variable dart
  counts) when you want to expose a scheduler's stragglers.

* A **Redis server** as the message broker. The queue and pub/sub exercises talk
  to a real Redis (the same Docker container Chapter 10 used for its Redis flag,
  mapped to host port 6380 to avoid colliding with any Redis on the default
  6379). `task ch11:redis-up` starts it; exercises that need it call
  `require_redis()` and skip cleanly with a friendly message if it is down.

Correctness anchor: any pi estimate built from these blocks must land within
PI_TOLERANCE of math.pi, asserted everywhere, so a distributed split that loses
or double-counts work fails loudly instead of drawing a pretty but wrong chart.
"""
import contextlib
import math
import os
import random
import subprocess
import time
import urllib.parse

# The Redis the broker exercises talk to. Our Docker container maps the server to
# host port 6380 so it never collides with a Redis already running on 6379.
REDIS_URL = os.environ.get("HPP_REDIS_URL", "redis://localhost:6380/0")

# A dart budget large enough that a single pure-Python block is a few hundred
# milliseconds — big enough to read a parallel signal out of timing noise, small
# enough that the serial baseline is a handful of seconds, not a minute.
DARTS_PER_BLOCK = 2_000_000
PI_TOLERANCE = 0.01


def estimate_pi_block(nbr_darts):
    """Count darts landing inside the quarter circle with a pure-Python loop.

    Pure Python (not numpy) on purpose: this is the GIL-bound, CPU-heavy unit of
    work whose only escape is *another interpreter* — on another core (IPython
    engine, Pool worker) or another machine (a real cluster). That is exactly the
    regime Chapter 11 is about.
    """
    inside = 0
    for _ in range(int(nbr_darts)):
        x = random.random()
        y = random.random()
        inside += x * x + y * y <= 1.0
    return inside


def pi_block_with_pid(nbr_darts):
    """Like estimate_pi_block, but also return the worker's pid.

    Lets the scheduler exercises tally how many darts each distinct engine/process
    actually handled — the per-engine load that reveals stragglers (ex03).
    """
    import os
    return (os.getpid(), estimate_pi_block(nbr_darts))


def noop():
    """A do-nothing callable for measuring pure round-trip latency (ex02)."""
    return None


def inc(x):
    """A trivially cheap callable so a call's cost is all messaging, not compute (ex02)."""
    return x + 1


def pi_from_counts(counts, total_darts):
    """Combine per-worker inside-counts into one pi estimate."""
    return sum(counts) * 4 / float(total_darts)


def assert_pi(pi_estimate):
    """Correctness anchor: the combined estimate must actually approximate pi."""
    assert abs(pi_estimate - math.pi) < PI_TOLERANCE, (
        f"pi estimate {pi_estimate} is not within {PI_TOLERANCE} of math.pi — "
        "the distributed split lost or double-counted work"
    )
    return pi_estimate


def uneven_blocks(n_blocks, base, spread, heavy_frac=0.15, seed=1234):
    """A deliberately *lopsided* list of dart counts for the scheduler exercises.

    A random handful of blocks (heavy_frac of them) are several times larger than
    the rest, scattered at *random positions* in the list — not periodically. That
    placement is the whole point: a direct view splits the list into one contiguous
    chunk per engine, so when the heavy blocks happen to cluster into a few chunks,
    those engines become stragglers while the rest finish early and sit idle. A
    load-balanced scheduler hands blocks out one at a time on demand, so no engine
    is left holding a heavy chunk alone. Seeded, so the lopsidedness — and which
    chunks get unlucky — is identical run to run.
    """
    rng = random.Random(seed)
    sizes = []
    for _ in range(n_blocks):
        if rng.random() < heavy_frac:
            factor = rng.uniform(4, spread)     # a rare, heavy block
        else:
            factor = rng.uniform(0.4, 1.2)      # the common, light block
        sizes.append(int(base * factor))
    return sizes


# --- Redis helpers -----------------------------------------------------------

def get_redis(**kwargs):
    """A Redis client pointed at the chapter's server (decode_responses off)."""
    import redis
    return redis.Redis.from_url(REDIS_URL, **kwargs)


def redis_available():
    """True if a Redis server answers PING within half a second."""
    try:
        get_redis(socket_connect_timeout=0.5).ping()
        return True
    except Exception:
        return False


EPHEMERAL_CONTAINER = "hpp-ch11-redis-ephemeral"


def _redis_port():
    return urllib.parse.urlparse(REDIS_URL).port or 6379


def _docker_available():
    try:
        subprocess.run(["docker", "info"], capture_output=True, timeout=10, check=True)
        return True
    except Exception:
        return False


@contextlib.contextmanager
def ephemeral_redis(wait_s=15):
    """Yield a Redis client, managing a throwaway container for the test's lifetime.

    The broker exercises wrap their measurement in this so they need no manual
    setup and leave nothing running afterwards:

      * If a Redis is already reachable at REDIS_URL — one you started yourself, or
        via `task ch11:redis-up` — reuse it and leave it completely alone (it is
        not ours to remove).
      * Otherwise, if Docker is available, start a throwaway `redis:7-alpine`
        container, wait for it to accept connections, yield a client, and ALWAYS
        remove the container on exit — even if the exercise raises.
      * If neither a Redis nor Docker is available, yield None so the caller can
        skip cleanly (this keeps the smoke target green on a machine with no
        Docker).
    """
    if redis_available():
        yield get_redis()       # reuse an existing server; do not tear it down
        return
    if not _docker_available():
        yield None              # nothing to talk to and nothing to start
        return

    port = _redis_port()
    subprocess.run(["docker", "rm", "-f", EPHEMERAL_CONTAINER], capture_output=True)
    subprocess.run(["docker", "run", "-d", "--name", EPHEMERAL_CONTAINER,
                    "-p", f"{port}:6379", "redis:7-alpine"],
                   check=True, capture_output=True)
    try:
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < wait_s:
            if redis_available():
                break
            time.sleep(0.3)
        else:
            raise RuntimeError(f"ephemeral Redis on port {port} did not become ready "
                               f"within {wait_s}s")
        yield get_redis()
    finally:
        subprocess.run(["docker", "rm", "-f", EPHEMERAL_CONTAINER], capture_output=True)
