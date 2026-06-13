"""ex03 — how many requests at once? Sweeping the concurrency limit.

The async crawler's speed comes from how many requests it keeps in flight. The obvious guess
is "more is always better — set the limit to N and pay one delay total." The book's Figure 9-4
says otherwise: past a few hundred concurrent requests the gains flatten and can reverse,
because the event loop's own single-threaded Python dispatch becomes the bottleneck once
completions arrive faster than it can hand them off.

This drill sweeps the connection limit across a wide range for two server delays (a slow one
and a fast one) and records total runtime, so we can see where — and whether, at this scale —
the knee shows up. We deliberately use more requests than the largest limit so that low limits
genuinely run in multiple waves.
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
from _workload import generate_urls  # noqa: E402

N_REQUESTS = 1000
LIMITS = [5, 10, 25, 50, 100, 250, 500, 1000]
DELAYS_MS = [50, 5]   # a "slow database" and a "fast cache"


async def _process(session, url):
    async with session.get(url) as response:
        return len(await response.text())


async def _run(base_url, num_iter, limit):
    connector = aiohttp.TCPConnector(limit=limit)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(_process(session, u))
                     for u in generate_urls(base_url, num_iter)]
    return sum(t.result() for t in tasks)


def sweep(base):
    """Return {delay_ms: [(limit, elapsed_s), ...]} measured against the live server."""
    out = {}
    for delay in DELAYS_MS:
        url = f"{base}/get?delay={delay}&name=sweep"
        row = []
        for limit in LIMITS:
            t = time.perf_counter()
            size = asyncio.run(_run(url, N_REQUESTS, limit))
            elapsed = time.perf_counter() - t
            assert size > 0
            row.append((limit, elapsed))
        out[delay] = row
    return out


def main():
    with running_server() as base:
        data = sweep(base)
    for delay, row in data.items():
        print(f"\ndelay={delay}ms, N={N_REQUESTS}")
        best = min(e for _, e in row)
        for limit, elapsed in row:
            bar = "#" * int(40 * best / elapsed)
            print(f"  limit {limit:>4}: {elapsed:6.3f}s  {bar}")


if __name__ == "__main__":
    main()
