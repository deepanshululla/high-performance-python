"""ex07 — fully async: hide the I/O *inside* the CPU time.

Batching (ex06) still stops the CPU dead while a burst of saves goes out. The full async
solution does better: it keeps one long-lived `ClientSession`, and after each hash it creates a
save task and then yields once with `await asyncio.sleep(0)`. That yield is the whole trick —
it hands the event loop a moment to push the in-flight saves forward *while the next hash is
being computed*. The I/O for hash N overlaps the CPU work for hash N+1, so at steady state the
I/O nearly disappears from the wall clock.

`asyncio.sleep(0)` doesn't sleep; it schedules a zero-delay wakeup and suspends, which forces a
trip through the event loop. Without it, a CPU loop never awaits anything real, so the loop
never runs the save tasks until the `TaskGroup` exits — at which point every save fires at once
and you've gained nothing. ex08 dissects that yield; here we measure the payoff against serial
and batched.
"""
import asyncio
import importlib.util
import pathlib
import sys
import time

import aiohttp

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir

from _server import running_server  # noqa: E402
from _workload import do_task, N_HASHES, URL_DELAY_MS, DEFAULT_DIFFICULTY  # noqa: E402


async def _save(session, url, result):
    async with session.post(url, data=result) as response:
        return await response.text()


async def run_full_async(save_url, num_iter, difficulty, yield_each=True):
    async with aiohttp.ClientSession() as session:
        async with asyncio.TaskGroup() as tg:
            for _ in range(num_iter):
                result = do_task(difficulty)
                tg.create_task(_save(session, save_url, result))
                if yield_each:
                    await asyncio.sleep(0)   # let pending saves advance during the next hash


def measure(save_url, num_iter=N_HASHES, difficulty=DEFAULT_DIFFICULTY, yield_each=True):
    t = time.perf_counter()
    asyncio.run(run_full_async(save_url, num_iter, difficulty, yield_each))
    return time.perf_counter() - t


def _load(name):
    p = HERE.parents[0] / name / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    serial_mod = _load("ex05_serial_cpu_io")
    batch_mod = _load("ex06_batched_pipeline")
    with running_server() as base:
        url = f"{base}/add?delay={URL_DELAY_MS}&name=full-async"
        serial_total, cpu_only = serial_mod.measure(url, N_HASHES, DEFAULT_DIFFICULTY)
        batched = batch_mod.measure(url, N_HASHES, DEFAULT_DIFFICULTY, batch_size=100)
        full = measure(url, N_HASHES, DEFAULT_DIFFICULTY, yield_each=True)

    print(f"full async CPU+I/O: {N_HASHES} hashes @ difficulty {DEFAULT_DIFFICULTY}, save @ {URL_DELAY_MS}ms")
    print(f"  serial    : {serial_total:.2f}s  ({serial_total / full:.2f}x slower)")
    print(f"  batched   : {batched:.2f}s  ({batched / full:.2f}x slower)")
    print(f"  full async: {full:.2f}s")
    print(f"  CPU floor : {cpu_only:.2f}s  (I/O fully hidden would land here)")
    print(f"  overhead over CPU floor: {full - cpu_only:.2f}s")


if __name__ == "__main__":
    main()
