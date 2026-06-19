"""ex02 — the latency tax of talking to engines (push, pull, apply round-trips).

Chapter 11 warns that the moment you go distributed you inherit *latency between
machines*. Even on one laptop, every `apply`, `push`, and `pull` is a message that
travels driver -> controller -> engine and back over ZeroMQ. That round-trip is
cheap in absolute terms (a millisecond or so), but it is a *fixed cost per call*,
and it is the thing that decides whether farming work out to a cluster speeds you
up or quietly slows you down.

We measure three things:

  * **Round-trip latency** — how long a do-nothing `apply_sync(lambda: None)` takes
    to one engine and to all engines. This is the floor: the price of saying
    anything at all to the cluster.
  * **Push bandwidth** — how long `push` takes as the payload grows from 1 KB to
    16 MB, and the effective MB/s once the payload is big enough to dominate the
    fixed latency.
  * **The tiny-task trap** — the same total work (a fixed number of dart blocks)
    delivered as many small `apply` calls versus one batched call. Many small
    calls pay the round-trip latency over and over; one batched call pays it once.

The lesson mirrors Chapter 10's Queue-overhead exercise: when the per-item work is
small, the communication *is* the cost, and the fix is always to make each message
carry more work.
"""
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[0]))

from _cluster import noop, inc  # noqa: E402
from _ipp import local_cluster, prepare_engines  # noqa: E402

N_ENGINES = 8
PING_REPEAT = 50                       # round-trips to average the latency over
PAYLOAD_SIZES = [1_000, 100_000, 1_000_000, 4_000_000, 16_000_000]  # bytes
TINY_CALLS = 200                       # number of trivial calls in the chatty trap


def measure():
    out = {}
    with local_cluster(N_ENGINES) as rc:
        prepare_engines(rc)   # so noop/inc resolve on the engines by reference
        one = rc[rc.ids[0]]   # a view onto a single engine
        allv = rc[:]          # a direct view onto every engine

        # --- round-trip latency: cost of a do-nothing call ---
        def ping_one():
            for _ in range(PING_REPEAT):
                one.apply_sync(noop)
        def ping_all():
            for _ in range(PING_REPEAT):
                allv.apply_sync(noop)
        t0 = time.perf_counter(); ping_one(); lat_one = (time.perf_counter() - t0) / PING_REPEAT
        t0 = time.perf_counter(); ping_all(); lat_all = (time.perf_counter() - t0) / PING_REPEAT
        out["lat_one_ms"] = lat_one * 1e3
        out["lat_all_ms"] = lat_all * 1e3

        # --- push bandwidth vs payload size ---
        push_rows = []
        for nbytes in PAYLOAD_SIZES:
            blob = b"x" * nbytes
            t0 = time.perf_counter()
            allv.push({"blob": blob}, block=True)
            dt = time.perf_counter() - t0
            push_rows.append((nbytes, dt))
        out["push"] = push_rows

        # --- the tiny-task trap: many chatty calls vs one batched call ---
        # The work per item is trivial on purpose (increment a number), so what we
        # are timing is pure messaging overhead, not compute. The "chatty" version
        # makes TINY_CALLS blocking round-trips in a loop — the shape of naive code
        # that calls the cluster once per item. The batched version hands the whole
        # list to one map call, paying the round-trip a handful of times.
        def chatty():
            return [allv.apply_sync(inc, i) for i in range(TINY_CALLS)]

        def batched():
            # A direct-view map splits the list into one chunk per engine, so the
            # whole batch costs a handful of round-trips instead of TINY_CALLS.
            return allv.map_sync(inc, list(range(TINY_CALLS)))

        t0 = time.perf_counter(); chatty(); out["tiny_s"] = time.perf_counter() - t0
        t0 = time.perf_counter(); batched(); out["batched_s"] = time.perf_counter() - t0

    return out


def main():
    r = measure()
    print(f"round-trip latency of a no-op apply ({PING_REPEAT} samples, {N_ENGINES} engines):")
    print(f"  to one engine  : {r['lat_one_ms']:6.2f} ms")
    print(f"  to all engines : {r['lat_all_ms']:6.2f} ms  (a fan-out, still one call)")
    print("push payload -> driver-to-all-engines time and effective bandwidth:")
    for nbytes, dt in r["push"]:
        mbps = (nbytes / 1e6) / dt
        print(f"  {nbytes/1e6:7.3f} MB : {dt*1e3:7.1f} ms  ({mbps:6.1f} MB/s)")
    print(f"tiny-task trap: {TINY_CALLS} trivial jobs (increment a number)")
    print(f"  chatty (one blocking call per job) : {r['tiny_s']:6.2f} s")
    print(f"  batched (one map call)             : {r['batched_s']:6.2f} s  "
          f"-> batching is {r['tiny_s'] / r['batched_s']:.0f}x faster")


if __name__ == "__main__":
    main()
