"""ex06 — pub/sub fan-out vs consumer-group load balancing.

The book draws a careful distinction between two ways messages reach consumers,
and it is the single most confused point in messaging systems. Both involve a
publisher and several consumers; what differs is *who gets each message*.

  * **Pub/sub fan-out** — every subscriber gets an identical copy of every
    message. The book's analogy is a newspaper: many people subscribe, and each
    edition is delivered to *all* of them. Use it to broadcast the same event to
    independent reactors (cache invalidation, live dashboards, audit logs).

  * **Consumer-group load balancing** — the consumers within one subscription
    *share* the messages; each message is handled by exactly one of them. The
    analogy is one household with a single subscription: the paper arrives once,
    and whoever picks it up first reads it. Use it to spread one stream of work
    across a pool of workers.

We model fan-out with Redis pub/sub (`PUBLISH`/`SUBSCRIBE`) and load balancing
with a Redis Streams consumer group (`XADD` + `XREADGROUP`). The same number of
messages is sent to four consumers under each model, and we count how many each
consumer actually received. The numbers make the distinction unmistakable: under
fan-out every consumer sees *all* the messages (so the system does K times the
delivery work); under a consumer group the messages are partitioned across the
consumers (so each does its share and the totals add up to one pass).
"""
import pathlib
import sys
import threading

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[0]))

from _cluster import get_redis, ephemeral_redis  # noqa: E402

CHANNEL = "hpp:ch11:ex06:events"
STREAM = "hpp:ch11:ex06:stream"
GROUP = "workers"
STOP = b"__STOP__"
N_MESSAGES = 500
N_CONSUMERS = 4


def fanout():
    """Redis pub/sub: every subscriber receives every message."""
    r = get_redis()
    counts = [0] * N_CONSUMERS
    barrier = threading.Barrier(N_CONSUMERS + 1)

    def subscriber(idx):
        ps = r.pubsub()
        ps.subscribe(CHANNEL)
        ps.get_message(timeout=1)        # swallow the subscribe-confirmation message
        barrier.wait()                    # signal "I am listening" before any publish
        c = 0
        for msg in ps.listen():
            if msg["type"] != "message":
                continue
            if msg["data"] == STOP:
                break
            c += 1
        counts[idx] = c
        ps.close()

    threads = [threading.Thread(target=subscriber, args=(i,)) for i in range(N_CONSUMERS)]
    for t in threads:
        t.start()
    barrier.wait()                        # all subscribers are listening now
    pub = get_redis()
    for i in range(N_MESSAGES):
        pub.publish(CHANNEL, f"event-{i}")
    pub.publish(CHANNEL, STOP)            # one STOP, fanned out to every subscriber
    for t in threads:
        t.join()
    return counts


def consumer_group():
    """Redis Streams consumer group: each message goes to exactly one consumer."""
    r = get_redis()
    r.delete(STREAM)
    for i in range(N_MESSAGES):
        r.xadd(STREAM, {"event": i})
    # MKSTREAM-safe group creation from the start of the stream.
    try:
        r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except Exception:
        r.xgroup_destroy(STREAM, GROUP)
        r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)

    counts = [0] * N_CONSUMERS

    def worker(idx):
        rc = get_redis()
        name = f"consumer-{idx}"
        c = 0
        while True:
            resp = rc.xreadgroup(GROUP, name, {STREAM: ">"}, count=10, block=500)
            if not resp:
                break                      # no more pending messages for this group
            for _stream, entries in resp:
                for msg_id, _fields in entries:
                    rc.xack(STREAM, GROUP, msg_id)
                    c += 1
            counts[idx] = c

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(N_CONSUMERS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return counts


def measure():
    with ephemeral_redis():
        return {"fanout": fanout(), "group": consumer_group()}


def main():
    r = measure()
    fo, gr = r["fanout"], r["group"]
    print(f"{N_MESSAGES} messages, {N_CONSUMERS} consumers")
    print(f"  pub/sub fan-out      : per-consumer {fo}  total {sum(fo)} "
          f"(= {N_CONSUMERS}x{N_MESSAGES}, every consumer got every message)")
    print(f"  consumer group (LB)  : per-consumer {gr}  total {sum(gr)} "
          f"(= {N_MESSAGES}, messages partitioned across consumers)")
    assert all(c == N_MESSAGES for c in fo), "fan-out: a subscriber missed messages"
    assert sum(gr) == N_MESSAGES, "consumer group: messages lost or duplicated"
    spread = max(gr) / min(gr) if min(gr) else float("inf")
    print(f"  fan-out does {sum(fo)//sum(gr)}x the delivery work; the group splits one pass "
          f"(load spread {spread:.2f}x)")


if __name__ == "__main__":
    main()
