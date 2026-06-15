"""ex07 — verifying one big number across CPUs, and the cost of an early-exit flag.

A different problem from "find all primes in a range": here we are handed a single
large number and must decide if it is prime, using all cores on that one number.
We split its factor space [3, sqrt(n)) across 8 workers. The catch is the
asymmetry between primes and nonprimes:

* A *nonprime* has a factor somewhere. One worker finds it and could stop the
  whole search early — IF it can tell the others. That signal needs interprocess
  communication: a shared flag.
* A *prime* has no factor, so no one can ever signal an early exit. Every worker
  grinds through its whole slice no matter what — and now the flag is pure
  overhead: instructions and locks added to the hottest loop for no benefit.

We compare six approaches against the same five numbers (a small nonprime, two
18-digit nonprimes, two 18-digit primes):

  serial            — one core, trial division, no IPC
  naive pool        — split across 8, no flag, no serial pre-check
  less naive pool   — quick serial pre-check for tiny factors, then split (no flag)
  manager.Value     — less-naive + a Manager proxy flag for early exit
  RawValue          — less-naive + a lock-free ctypes flag
  mmap (redux)      — less-naive + an anonymous shared-memory byte, loop unrolled

The story the numbers tell: the flag *helps* on the big nonprimes (early exit
beats the check cost) but *hurts* on primes (no early exit, only cost). RawValue
and mmap are far cheaper to poll than a Manager proxy, so they claw most of that
cost back. The plain "less naive pool" is a stubbornly good benchmark — exactly
the book's point that the dumb-but-good-enough solution is hard to beat.

There is a seventh approach — a **Redis** flag — that only runs if a Redis server
is reachable (see REDIS_URL; the repo ships a Docker one on port 6380, started by
`task ch10:redis-up`). Redis is the book's language-agnostic option: the flag lives
in an external server any tool can read, at the cost of a TCP round-trip per poll.
We expect it to land among the slow approaches, alongside (or behind) manager.Value.
If Redis is down the approach is skipped cleanly, so the suite still runs without
Docker.

Most shared flags live as module globals and rely on fork inheritance (see _mp.py);
the pool is created *after* they exist so the workers inherit them. The Redis
client is the exception: a socket must NOT be shared across a fork, so each worker
lazily opens its *own* connection on first use (the global starts as None at fork
time, so no socket is inherited).
"""
import math
import mmap
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[0]))

from perf import time_s  # noqa: E402
from _primes import check_prime, create_range, VALIDATION_NUMBERS  # noqa: E402
from _mp import CTX  # noqa: E402

NBR_PROCESSES = 8
SERIAL_CHECK_CUTOFF = 21
CHECK_EVERY = 1000
FLAG_CLEAR = 0
FLAG_SET = 1
REPEAT = 2            # best of N (the book uses min of 20); the 18-digit primes are ~1s each

# Redis flag config. Our Docker container maps the server to host port 6380 to
# avoid colliding with any Redis already on the default 6379.
REDIS_URL = os.environ.get("HPP_REDIS_URL", "redis://localhost:6380/0")
REDIS_FLAG = "hpp_primes_flag"
REDIS_CLEAR = b"0"
REDIS_SET = b"1"


# --- shared flags as module globals (inherited by forked workers) ----------------
_raw_value = CTX.RawValue("b", FLAG_CLEAR)
_sh_mem = mmap.mmap(-1, 1)
_mgr = CTX.Manager()
_mgr_value = _mgr.Value("b", FLAG_CLEAR)

# The Redis client is created lazily, per process — NOT at import — so a forked
# worker never inherits (and corrupts) the parent's socket. Stays None until first
# use inside whichever process needs it.
_rds = None


def _get_rds():
    global _rds
    if _rds is None:
        import redis
        _rds = redis.Redis.from_url(REDIS_URL)
    return _rds


def redis_available():
    """True if a Redis server answers PING — decides whether ex07 includes it."""
    try:
        import redis
        redis.Redis.from_url(REDIS_URL, socket_connect_timeout=0.5).ping()
        return True
    except Exception:
        return False


# --- range-checkers, one per approach -------------------------------------------

def _check_range_plain(n_from_i_to_i):
    """No flag: just sweep this slice for a factor."""
    (n, (from_i, to_i)) = n_from_i_to_i
    if n % 2 == 0:
        return False
    for i in range(from_i, int(to_i), 2):
        if n % i == 0:
            return False
    return True


def _check_range_manager(n_from_i_to_i):
    (n, (from_i, to_i)) = n_from_i_to_i
    if n % 2 == 0:
        return False
    check_every = CHECK_EVERY
    for i in range(from_i, int(to_i), 2):
        check_every -= 1
        if not check_every:
            if _mgr_value.value == FLAG_SET:
                return False
            check_every = CHECK_EVERY
        if n % i == 0:
            _mgr_value.value = FLAG_SET
            return False
    return True


def _check_range_rawvalue(n_from_i_to_i):
    (n, (from_i, to_i)) = n_from_i_to_i
    if n % 2 == 0:
        return False
    check_every = CHECK_EVERY
    for i in range(from_i, int(to_i), 2):
        check_every -= 1
        if not check_every:
            if _raw_value.value == FLAG_SET:
                return False
            check_every = CHECK_EVERY
        if n % i == 0:
            _raw_value.value = FLAG_SET
            return False
    return True


def _check_range_mmap(n_from_i_to_i):
    """The book's 'redux': unroll the CHECK_EVERY counter into a two-level loop
    so the inner loop carries no per-iteration bookkeeping at all."""
    (n, (from_i, to_i)) = n_from_i_to_i
    if n % 2 == 0:
        return False
    for outer in range(from_i, int(to_i), CHECK_EVERY):
        upper = min(int(to_i), outer + CHECK_EVERY)
        for i in range(outer, upper, 2):
            if n % i == 0:
                _sh_mem.seek(0)
                _sh_mem.write_byte(FLAG_SET)
                return False
        _sh_mem.seek(0)
        if _sh_mem.read_byte() == FLAG_SET:
            return False
    return True


def _check_range_redis(n_from_i_to_i):
    """Same early-exit logic, but the flag lives in an external Redis server, so
    every poll is a TCP round-trip. Each worker uses its own lazy connection."""
    (n, (from_i, to_i)) = n_from_i_to_i
    if n % 2 == 0:
        return False
    rds = _get_rds()
    check_every = CHECK_EVERY
    for i in range(from_i, int(to_i), 2):
        check_every -= 1
        if not check_every:
            if rds.get(REDIS_FLAG) == REDIS_SET:
                return False
            check_every = CHECK_EVERY
        if n % i == 0:
            rds.set(REDIS_FLAG, REDIS_SET)
            return False
    return True


def _ranges(n, from_i):
    to_i = int(math.sqrt(n)) + 1
    rtc = create_range(from_i, to_i, NBR_PROCESSES)
    return list(zip([n] * len(rtc), rtc))


# --- the six approaches; each returns True if n is prime -------------------------

def via_serial(n, pool):
    return check_prime(n)


def via_naive_pool(n, pool):
    results = pool.map(_check_range_plain, _ranges(n, 3))
    return False not in results


def via_less_naive_pool(n, pool):
    if not _check_range_plain((n, (3, SERIAL_CHECK_CUTOFF))):
        return False
    return False not in pool.map(_check_range_plain, _ranges(n, SERIAL_CHECK_CUTOFF))


def via_manager(n, pool):
    _mgr_value.value = FLAG_CLEAR
    if not _check_range_plain((n, (3, SERIAL_CHECK_CUTOFF))):
        return False
    return False not in pool.map(_check_range_manager, _ranges(n, SERIAL_CHECK_CUTOFF))


def via_rawvalue(n, pool):
    _raw_value.value = FLAG_CLEAR
    if not _check_range_plain((n, (3, SERIAL_CHECK_CUTOFF))):
        return False
    return False not in pool.map(_check_range_rawvalue, _ranges(n, SERIAL_CHECK_CUTOFF))


def via_mmap(n, pool):
    _sh_mem.seek(0)
    _sh_mem.write_byte(FLAG_CLEAR)
    if not _check_range_plain((n, (3, SERIAL_CHECK_CUTOFF))):
        return False
    return False not in pool.map(_check_range_mmap, _ranges(n, SERIAL_CHECK_CUTOFF))


def via_redis(n, pool):
    _get_rds().set(REDIS_FLAG, REDIS_CLEAR)
    if not _check_range_plain((n, (3, SERIAL_CHECK_CUTOFF))):
        return False
    return False not in pool.map(_check_range_redis, _ranges(n, SERIAL_CHECK_CUTOFF))


# The six batteries-included approaches, always run. Redis is slotted in after
# manager.Value (grouping it with the other slow, externally-shared flags) only
# when a server is reachable — see active_approaches().
APPROACHES = [
    ("serial", via_serial),
    ("naive pool", via_naive_pool),
    ("less naive pool", via_less_naive_pool),
    ("manager.Value", via_manager),
    ("RawValue", via_rawvalue),
    ("mmap (redux)", via_mmap),
]
REDIS_APPROACH = ("Redis", via_redis)


def active_approaches():
    """The approaches to run now: the six, plus Redis after manager.Value if up."""
    if not redis_available():
        return list(APPROACHES)
    out = []
    for entry in APPROACHES:
        out.append(entry)
        if entry[0] == "manager.Value":
            out.append(REDIS_APPROACH)
    return out


def measure():
    """Return {approach: {label: seconds}} timing every number under every method.

    Insertion order follows active_approaches(), so callers can iterate out.keys()
    to render rows/bars without knowing whether Redis was included.
    """
    pool = CTX.Pool(NBR_PROCESSES)
    out = {}
    try:
        for name, fn in active_approaches():
            row = {}
            for label, n, is_prime in VALIDATION_NUMBERS:
                got = {}

                def once(n=n, fn=fn, got=got):
                    got["r"] = fn(n, pool)
                t = time_s(once, number=1, repeat=REPEAT)
                assert got["r"] == is_prime, f"{name} got {got['r']} for {label}"
                row[label] = t
            out[name] = row
    finally:
        pool.close()
        pool.join()
    return out


def main():
    out = measure()
    labels = [lbl for lbl, _, _ in VALIDATION_NUMBERS]
    have_redis = "Redis" in out
    print(f"verify primality across {NBR_PROCESSES} workers (best of {REPEAT}, ms)")
    if not have_redis:
        print(f"  [Redis skipped — no server at {REDIS_URL}; start one with "
              f"`task ch10:redis-up`]")
    head = "  {:<18}".format("approach") + "".join(f"{l.split()[0][:6]:>9}" for l in labels)
    print(head)
    for name in out:
        cells = "".join(f"{out[name][l] * 1000:9.2f}" for l in labels)
        print(f"  {name:<18}{cells}")
    print("  (columns: small-nonprime, nonprime1, nonprime2, prime1, prime2)")


if __name__ == "__main__":
    main()
