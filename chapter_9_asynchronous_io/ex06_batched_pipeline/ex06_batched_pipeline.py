"""ex06 — batching (pipelining): most of the async win, almost none of the rewrite.

Going fully async means refactoring the whole call chain into coroutines. The chapter offers a
cheaper middle path: keep the CPU loop synchronous, but instead of saving each result the
instant it's computed, queue results and flush them to the database in concurrent bursts. When
the queue hits `batch_size`, we spin up a short-lived event loop, fire all those saves at once,
wait for them together, and resume the CPU loop.

The structure of the surrounding program barely changes — you swap `save(result)` for
`batcher.save(result)` and wrap the loop in a context manager so the final partial batch
flushes on exit. We still pay an I/O pause, but during it we do `batch_size` requests instead
of one, so the per-result delay is amortized across the whole batch.
"""
import asyncio
import pathlib
import sys
import time

import aiohttp

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir

import importlib.util  # noqa: E402

from _server import running_server  # noqa: E402
from _workload import do_task, N_HASHES, URL_DELAY_MS, DEFAULT_DIFFICULTY  # noqa: E402


class AsyncBatcher:
    """Queue results and flush them to the database in concurrent bursts of `batch_size`."""

    def __init__(self, url, batch_size):
        self.url = url
        self.batch_size = batch_size
        self.batch = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.flush()

    def save(self, result):
        self.batch.append(result)
        if len(self.batch) >= self.batch_size:
            self.flush()

    def flush(self):
        if not self.batch:
            return
        asyncio.run(self._aflush())   # a temporary event loop just to run this burst
        self.batch.clear()

    async def _aflush(self):
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch(result, session) for result in self.batch]
            await asyncio.gather(*tasks)

    async def _fetch(self, result, session):
        async with session.post(self.url, data=result) as response:
            return await response.text()


def run_batched(save_url, num_iter, difficulty, batch_size):
    with AsyncBatcher(save_url, batch_size) as batcher:
        for _ in range(num_iter):
            batcher.save(do_task(difficulty))


def measure(save_url, num_iter=N_HASHES, difficulty=DEFAULT_DIFFICULTY, batch_size=100):
    t = time.perf_counter()
    run_batched(save_url, num_iter, difficulty, batch_size)
    return time.perf_counter() - t


def _load_serial():
    p = HERE.parents[0] / "ex05_serial_cpu_io" / "ex05_serial_cpu_io.py"
    spec = importlib.util.spec_from_file_location("ex05_serial_cpu_io", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    serial_mod = _load_serial()
    with running_server() as base:
        url = f"{base}/add?delay={URL_DELAY_MS}&name=batched"
        serial_total, _ = serial_mod.measure(url, N_HASHES, DEFAULT_DIFFICULTY)
        batched = measure(url, N_HASHES, DEFAULT_DIFFICULTY, batch_size=100)

    print(f"batched CPU+I/O: {N_HASHES} hashes @ difficulty {DEFAULT_DIFFICULTY}, batch=100, save @ {URL_DELAY_MS}ms")
    print(f"  serial : {serial_total:.2f}s")
    print(f"  batched: {batched:.2f}s")
    print(f"  speedup: {serial_total / batched:.2f}x")


if __name__ == "__main__":
    main()
