"""ex07 — delivery guarantees: at-most-once loss vs at-least-once duplication.

Two of the book's key questions to ask of any queue: *"Does a consumer have to
acknowledge that it is done processing a message? What happens if a consumer
fails midway?"* and *"are messages guaranteed to be delivered at least once? at
most once?"* These are not abstract — they decide what your system does when (not
if) a worker dies mid-job, and there is no free lunch: you choose which way to be
wrong.

We model the dangerous moment precisely: a consumer takes a message, does the
work, and then **crashes before it can confirm completion**. That is the realistic
failure — the crash lands in the window between finishing the work and recording
that fact. We replay the identical stream of messages with the identical crash
schedule under two delivery models:

  * **At-most-once** — a plain Redis list, popped with `LPOP`. The pop *removes*
    the message immediately, so if the consumer crashes before recording its
    result, the message is simply gone. No message is ever processed twice, but
    crashed-in-flight messages are **lost**.

  * **At-least-once** — a Redis Streams consumer group. `XREADGROUP` delivers a
    message but leaves it *pending* until the consumer `XACK`s it. A crash before
    the ack leaves the message pending; a recovery consumer reclaims it with
    `XAUTOCLAIM` and processes it again. Nothing is lost, but the reclaimed
    messages are processed **twice** (a duplicate).

The same eight crashes produce eight *lost* messages under at-most-once and eight
*duplicate* processings under at-least-once — the whole tradeoff in one pair of
numbers.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[0]))

from _cluster import ephemeral_redis  # noqa: E402

LIST_KEY = "hpp:ch11:ex07:list"
STREAM = "hpp:ch11:ex07:stream"
GROUP = "workers"
N_MESSAGES = 200
CRASH_EVERY = 25          # crash after every 25th message (8 crashes over 200)


def at_most_once(r):
    """Plain list + LPOP: a crash after the pop loses the in-flight message."""
    r.delete(LIST_KEY)
    pipe = r.pipeline()
    for i in range(N_MESSAGES):
        pipe.rpush(LIST_KEY, i)
    pipe.execute()

    processed = []            # message ids whose result we actually recorded
    delivered = 0
    while True:
        val = r.lpop(LIST_KEY)
        if val is None:
            break
        mid = int(val)
        delivered += 1
        # ... do the work ...
        if delivered % CRASH_EVERY == 0:
            # CRASH here: work done, but we die before recording. The LPOP already
            # removed the message, so it is gone — nobody will ever redo it.
            continue
        processed.append(mid)
    unique = set(processed)
    return {"delivered": delivered, "unique": len(unique),
            "lost": N_MESSAGES - len(unique), "duplicated": len(processed) - len(unique)}


def at_least_once(r):
    """Streams group + XACK: a crash before ack leaves the message reclaimable."""
    r.delete(STREAM)
    for i in range(N_MESSAGES):
        r.xadd(STREAM, {"id": i})
    try:
        r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except Exception:
        r.xgroup_destroy(STREAM, GROUP)
        r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)

    processed = []            # every processing, including duplicates
    delivered = 0

    # --- primary consumer: reads, works, acks — but crashes before some acks ---
    while True:
        resp = r.xreadgroup(GROUP, "primary", {STREAM: ">"}, count=1, block=200)
        if not resp:
            break
        for _stream, entries in resp:
            for msg_id, fields in entries:
                mid = int(fields[b"id"])
                delivered += 1
                # ... do the work ...
                if delivered % CRASH_EVERY == 0:
                    # CRASH here: work done, but we die before XACK. The message
                    # stays PENDING in the group and can be reclaimed later.
                    processed.append(mid)
                    continue
                r.xack(STREAM, GROUP, msg_id)
                processed.append(mid)

    # --- recovery consumer: reclaim anything left pending and reprocess it ---
    start = "0-0"
    while True:
        msg_id, entries, _deleted = r.xautoclaim(
            STREAM, GROUP, "recovery", min_idle_time=0, start_id=start, count=50)
        if not entries:
            break
        for claimed_id, fields in entries:
            mid = int(fields[b"id"])
            # ... redo the work (this is the duplicate) ...
            r.xack(STREAM, GROUP, claimed_id)
            processed.append(mid)
        start = msg_id

    unique = set(processed)
    return {"delivered": delivered, "unique": len(unique),
            "lost": N_MESSAGES - len(unique), "duplicated": len(processed) - len(unique)}


def measure():
    with ephemeral_redis() as r:
        if r is None:
            return None
        return {"at_most_once": at_most_once(r), "at_least_once": at_least_once(r)}


def main():
    res = measure()
    if res is None:
        print("[skipped] no Redis reachable and Docker unavailable — cannot run an "
              "ephemeral broker.")
        return
    crashes = N_MESSAGES // CRASH_EVERY
    print(f"{N_MESSAGES} messages, a consumer crash after every {CRASH_EVERY}th "
          f"({crashes} crashes), each crash landing after the work but before the confirm")
    for name, label in [("at_most_once", "at-most-once (list + LPOP)"),
                        ("at_least_once", "at-least-once (stream + XACK)")]:
        s = res[name]
        print(f"  {label:<30} processed-once {s['unique']:>3}/{N_MESSAGES}  "
              f"lost {s['lost']:>2}  duplicated {s['duplicated']:>2}")
    assert res["at_most_once"]["lost"] == crashes, "expected one loss per crash"
    assert res["at_least_once"]["lost"] == 0, "at-least-once must lose nothing"
    assert res["at_least_once"]["duplicated"] == crashes, "expected one duplicate per crash"
    print("  the same crashes cost at-most-once its messages and at-least-once its uniqueness — "
          "you pick which way to be wrong")


if __name__ == "__main__":
    main()
