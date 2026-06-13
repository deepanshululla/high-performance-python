"""ex02 — the same crawl, asynchronous: stack the requests and hide the wait.

The structure barely changes from ex01. Instead of calling `process` in a loop, we wrap each
fetch in a `TaskGroup` task and let the event loop run them concurrently. The single thread
never does two things at literally the same instant, but while one coroutine sits in I/O wait,
the loop hands control to another that's ready — so the per-request 50 ms delays overlap
instead of stacking.

`aiohttp.ClientSession` caps simultaneous connections at 100 by default, so N requests run in
ceil(N / 100) waves of ~one delay each. With N=200 that's two waves ≈ 2 × delay, not the
serial N × delay. We measure both serial and async here so the speedup is a real ratio on this
machine, not a quote from the book.
"""
import asyncio
import pathlib
import sys

import aiohttp

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root -> perf
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir -> _server, _workload

import time  # noqa: E402

from _server import running_server  # noqa: E402
from _workload import generate_urls, N_REQUESTS, URL_DELAY_MS, DEFAULT_CONCURRENCY  # noqa: E402
import importlib.util  # noqa: E402


async def process(session, url):
    async with session.get(url) as response:
        return len(await response.text())


async def run_async(base_url: str, num_iter: int, concurrency: int = DEFAULT_CONCURRENCY) -> int:
    """Fetch every URL concurrently via a TaskGroup; return the summed body length."""
    tasks = []
    connector = aiohttp.TCPConnector(limit=concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with asyncio.TaskGroup() as tg:
            for url in generate_urls(base_url, num_iter):
                tasks.append(tg.create_task(process(session, url)))
    return sum(t.result() for t in tasks)


def measure_async(base_url, num_iter=N_REQUESTS, concurrency=DEFAULT_CONCURRENCY):
    """Return (response_size, elapsed_seconds) for one async run."""
    t = time.perf_counter()
    size = asyncio.run(run_async(base_url, num_iter, concurrency))
    return size, time.perf_counter() - t


def _load_serial():
    """Borrow ex01's serial runner so the speedup is measured against identical work."""
    p = HERE.parents[0] / "ex01_serial_crawler" / "ex01_serial_crawler.py"
    spec = importlib.util.spec_from_file_location("ex01_serial_crawler", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    serial_mod = _load_serial()
    with running_server() as base:
        url = f"{base}/get?delay={URL_DELAY_MS}&name=crawl"
        serial_size, serial_t = serial_mod.measure(url, N_REQUESTS)
        async_size, async_t = measure_async(url, N_REQUESTS)

    assert serial_size > 0 and async_size > 0, "correctness anchor failed"
    waves = -(-N_REQUESTS // DEFAULT_CONCURRENCY)  # ceil
    print(f"crawl: {N_REQUESTS} requests @ {URL_DELAY_MS}ms, concurrency={DEFAULT_CONCURRENCY}")
    print(f"  serial : {serial_t:.2f}s")
    print(f"  async  : {async_t:.2f}s   ({waves} waves of ~{URL_DELAY_MS}ms)")
    print(f"  speedup: {serial_t / async_t:.1f}x")


if __name__ == "__main__":
    main()
