"""A tiny delay-capable HTTP server — the shared 'slow I/O' every Chapter 9 drill talks to.

The book's web-crawler examples lean on a custom HTTP server that takes a `delay`
parameter (in milliseconds) and pauses that long before responding, so we can dial in a
realistic I/O latency without depending on a real network. This module is that server,
plus a little plumbing to launch it from a benchmark.

Two endpoints, both honoring `?delay=<ms>&name=<label>`:

    GET  /get   -> returns a short text body after sleeping `delay` ms (the crawler target)
    POST /add   -> accepts a body, returns {"ok": true} after sleeping `delay` ms (the "save
                   to database" target for the CPU+I/O workload)

The server is async itself (one `aiohttp` app, single thread, event loop), which is exactly
why it can hold many simultaneous connections open during their `delay` sleep — the premise
the whole chapter rests on. It records the wall-clock start/stop of every request in a small
in-memory log so the timeline-style exercises (ex02, ex07) can show requests overlapping.

Run standalone:
    .venv/bin/python chapter_9_asynchronous_io/_server.py --port 8080

Use from a benchmark:
    from _server import running_server
    with running_server(default_delay_ms=50) as base:   # base == "http://127.0.0.1:<port>"
        ...                                              # spawned as a subprocess, torn down on exit
"""
import argparse
import asyncio
import contextlib
import os
import socket
import subprocess
import sys
import time
import urllib.request

from aiohttp import web

# Process-wide request log: list of (name, t_start, t_end) in perf_counter seconds.
# Used by /stats so a client can pull the server-side timeline after a run.
_REQUEST_LOG: list[tuple[str, float, float]] = []
_T0 = time.perf_counter()


def _delay_seconds(request) -> float:
    raw = request.query.get("delay", "0")
    try:
        return max(0.0, float(raw) / 1000.0)
    except ValueError:
        return 0.0


async def _handle(request, *, read_body: bool) -> web.Response:
    name = request.query.get("name", "anon")
    start = time.perf_counter() - _T0
    if read_body:
        await request.read()
    await asyncio.sleep(_delay_seconds(request))
    end = time.perf_counter() - _T0
    _REQUEST_LOG.append((name, start, end))
    # A small, deterministic body so clients can sum response lengths as a correctness anchor.
    body = f"response:{name}:{len(_REQUEST_LOG)}"
    return web.Response(text=body)


async def handle_get(request):
    return await _handle(request, read_body=False)


async def handle_add(request):
    return await _handle(request, read_body=True)


async def handle_stats(request):
    return web.json_response({"count": len(_REQUEST_LOG), "log": _REQUEST_LOG})


async def handle_reset(request):
    _REQUEST_LOG.clear()
    return web.json_response({"ok": True})


def build_app() -> web.Application:
    app = web.Application()
    app.add_routes([
        web.get("/get", handle_get),
        web.post("/add", handle_add),
        web.get("/stats", handle_stats),
        web.post("/reset", handle_reset),
    ])
    return app


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def running_server(port: int | None = None, ready_timeout: float = 10.0):
    """Spawn the server as a subprocess; yield its base URL; tear it down on exit.

    Running it in a *separate process* (not a background thread in the client's own event
    loop) keeps the server's event loop from competing with the client's for the GIL, so the
    client's measured concurrency reflects the client, not contention with the server.
    """
    port = port or _free_port()
    base = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.perf_counter() + ready_timeout
        while True:
            try:
                with urllib.request.urlopen(f"{base}/get?delay=0", timeout=0.5) as r:
                    r.read()
                break
            except Exception:
                if time.perf_counter() > deadline:
                    raise RuntimeError("server did not come up in time")
                time.sleep(0.05)
        yield base
    finally:
        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=5)
        if proc.poll() is None:
            proc.kill()


def main():
    parser = argparse.ArgumentParser(description="Delay-capable HTTP server for Chapter 9.")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    web.run_app(build_app(), host="127.0.0.1", port=args.port, print=None)


if __name__ == "__main__":
    main()
