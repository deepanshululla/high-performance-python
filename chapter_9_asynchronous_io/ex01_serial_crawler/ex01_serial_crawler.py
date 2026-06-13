"""ex01 — the serial crawler: one request, wait, next request, repeat.

This is the baseline the rest of the chapter beats. We fetch N URLs with the synchronous
`requests` library, summing the length of every response body. Because each call blocks until
its response arrives, the total runtime is essentially N × delay plus overhead — the program
spends almost all its life parked in I/O wait, holding the CPU but doing nothing with it.

The point of measuring it is to have an honest floor: every speedup later is quoted against
this number on this machine, not against the book's laptop.
"""
import pathlib
import sys

import requests

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root -> perf
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir -> _server, _workload

from perf import time_s  # noqa: E402
from _server import running_server  # noqa: E402
from _workload import generate_urls, N_REQUESTS, URL_DELAY_MS  # noqa: E402


def run_serial(base_url: str, num_iter: int) -> int:
    """Fetch every URL one at a time; return the summed response-body length."""
    response_size = 0
    with requests.Session() as session:
        for url in generate_urls(base_url, num_iter):
            response = session.get(url)
            response_size += len(response.text)
    return response_size


def measure(base_url: str, num_iter: int = N_REQUESTS):
    """Return (response_size, elapsed_seconds) for one serial run."""
    result = {}

    def once():
        result["size"] = run_serial(base_url, num_iter)

    elapsed = time_s(once, number=1, repeat=1)
    return result["size"], elapsed


def main():
    with running_server() as base:
        url = f"{base}/get?delay={URL_DELAY_MS}&name=serial"
        size, elapsed = measure(url, N_REQUESTS)

    ideal = N_REQUESTS * URL_DELAY_MS / 1000
    assert size > 0, "no bytes returned — server/correctness anchor failed"
    print(f"serial crawler: {N_REQUESTS} requests @ {URL_DELAY_MS}ms")
    print(f"  bytes summed : {size}")
    print(f"  elapsed      : {elapsed:.2f}s")
    print(f"  ideal floor  : {ideal:.2f}s  (N x delay, no overlap)")
    print(f"  overhead     : {elapsed - ideal:.2f}s")


if __name__ == "__main__":
    main()
