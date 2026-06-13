"""ex08 — the `await asyncio.sleep(0)` knob: starvation on one side, overhead on the other.

ex07 dropped a `sleep(0)` after every hash and got near-perfect CPU/I/O overlap. This drill
takes that one line and turns it into a dial: yield every K iterations, for K from 1 (every
time) up through "never," and watch what each choice costs.

- yield **never**: the CPU loop never awaits anything real, so the event loop never runs the
  queued save tasks. They all fire at the `TaskGroup` exit, in waves bounded by the connection
  limit — no overlap at all. This is the failure mode the chapter warns about: the I/O is
  *added back on* at the end instead of hidden.
- yield **every iteration**: maximum overlap, but every yield is a real context switch with its
  own cost; in a tight loop that overhead can start to show.
- yield **every ~K**: the book's advice — yield often enough that pending I/O keeps draining
  (roughly every 50–100 ms of CPU work), but not so often that switching dominates.

To make the starvation cost visible we deliberately constrain the "database" to a small
connection limit (CONN_LIMIT), so the queued saves drain in many waves rather than one or two.
With a generous limit the end-of-run drain is a single wave and the penalty hides in the noise
— which is itself the book's point that a low-throughput server erases the benefit of async.
We measure total runtime for each K against the pure-CPU floor, so the cost of starving the
loop (large gap) and the cost of over-yielding (small but nonzero) are both visible.
"""
import asyncio
import pathlib
import sys
import time

import aiohttp

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir

from _server import running_server  # noqa: E402
from _workload import do_task, N_HASHES, URL_DELAY_MS, DEFAULT_DIFFICULTY  # noqa: E402

# K values to test; 0 means "never yield" (the starvation case).
YIELD_EVERY = [1, 2, 5, 10, 0]
# Constrained "database" throughput so the end-of-run drain spans many waves and the cost of
# starving the loop is visible rather than buried in noise (see module docstring).
CONN_LIMIT = 10


async def _save(session, url, result):
    async with session.post(url, data=result) as response:
        return await response.text()


async def _run(save_url, num_iter, difficulty, yield_every):
    connector = aiohttp.TCPConnector(limit=CONN_LIMIT)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with asyncio.TaskGroup() as tg:
            for i in range(num_iter):
                result = do_task(difficulty)
                tg.create_task(_save(session, save_url, result))
                if yield_every and (i % yield_every == 0):
                    await asyncio.sleep(0)


def measure_one(save_url, yield_every, num_iter=N_HASHES, difficulty=DEFAULT_DIFFICULTY):
    t = time.perf_counter()
    asyncio.run(_run(save_url, num_iter, difficulty, yield_every))
    return time.perf_counter() - t


def cpu_floor(num_iter=N_HASHES, difficulty=DEFAULT_DIFFICULTY):
    t = time.perf_counter()
    for _ in range(num_iter):
        do_task(difficulty)
    return time.perf_counter() - t


def sweep(base):
    """Return (cpu_only, [(yield_every, elapsed), ...])."""
    url = f"{base}/add?delay={URL_DELAY_MS}&name=sleep0"
    cpu_only = cpu_floor()
    rows = [(k, measure_one(url, k)) for k in YIELD_EVERY]
    return cpu_only, rows


def main():
    with running_server() as base:
        cpu_only, rows = sweep(base)
    print(f"sleep(0) cadence: {N_HASHES} hashes @ difficulty {DEFAULT_DIFFICULTY}, save @ {URL_DELAY_MS}ms, conn limit {CONN_LIMIT}")
    print(f"  CPU floor (no I/O): {cpu_only:.2f}s\n")
    for k, elapsed in rows:
        label = "never (starved)" if k == 0 else f"every {k}"
        over = elapsed - cpu_only
        print(f"  yield {label:>16}: {elapsed:5.2f}s   (+{over:.2f}s over CPU floor)")


if __name__ == "__main__":
    main()
