"""ex05 — CPU work that must save its results: the serial version.

The second half of the chapter mixes a CPU-bound task with I/O. Here the CPU task is a bcrypt
hash (tunably slow, see _workload.do_task) and after each hash we POST the result to the
"database" — our delay server — and wait for the reply before computing the next hash.

This is the baseline for ex06 (batched) and ex07 (full async). The lesson it sets up: the
serial version pays the full I/O delay after *every* CPU task, and that wait time is pure
waste — the CPU sits idle during it when it could be computing the next hash. We measure the
total, the CPU-only time (I/O disabled), and the difference, which is the I/O wait we're about
to reclaim.
"""
import pathlib
import sys
import time

import requests

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir

from _server import running_server  # noqa: E402
from _workload import do_task, N_HASHES, URL_DELAY_MS, DEFAULT_DIFFICULTY  # noqa: E402


def run_serial(save_url, num_iter, difficulty, save=True):
    """Hash num_iter strings; POST each result and wait, unless save=False (CPU-only control)."""
    n = 0
    with requests.Session() as session:
        for _ in range(num_iter):
            result = do_task(difficulty)
            if save:
                response = session.post(save_url, data=result)
                response.raise_for_status()
            n += 1
    return n


def measure(save_url, num_iter=N_HASHES, difficulty=DEFAULT_DIFFICULTY):
    """Return (total_seconds, cpu_only_seconds)."""
    t = time.perf_counter()
    run_serial(save_url, num_iter, difficulty, save=True)
    total = time.perf_counter() - t

    t = time.perf_counter()
    run_serial(save_url, num_iter, difficulty, save=False)
    cpu_only = time.perf_counter() - t
    return total, cpu_only


def main():
    with running_server() as base:
        url = f"{base}/add?delay={URL_DELAY_MS}&name=serial-save"
        total, cpu_only = measure(url, N_HASHES, DEFAULT_DIFFICULTY)

    io_floor = N_HASHES * URL_DELAY_MS / 1000
    print(f"serial CPU+I/O: {N_HASHES} hashes @ difficulty {DEFAULT_DIFFICULTY}, save @ {URL_DELAY_MS}ms")
    print(f"  total (CPU+I/O): {total:.2f}s")
    print(f"  CPU only       : {cpu_only:.2f}s")
    print(f"  I/O floor      : {io_floor:.2f}s  (N x delay)")
    print(f"  I/O wait share : {100 * (total - cpu_only) / total:.0f}% of total is I/O")


if __name__ == "__main__":
    main()
