"""FastAPI memory-leak demo — the ASGI equivalent of Dozer.

Dozer is WSGI middleware, so it can't wrap a FastAPI (ASGI) app. Instead we expose
a `/_memory` endpoint that does what Dozer's web UI does:
  * report process RSS,
  * show live object-type counts (via objgraph / gc) — watch a type climb = leak,
  * show tracemalloc's top allocation sites (where the leak was allocated).

Run it:
    uv run uvicorn leaky_api:app --port 8000      # from chapter_2/

Then drive a leak and watch it grow:
    curl localhost:8000/_memory                   # baseline
    for i in $(seq 1 20); do curl -s localhost:8000/leak?n=1000 >/dev/null; done
    curl localhost:8000/_memory                   # Widget count + RSS have climbed
"""
import gc
import tracemalloc

import objgraph
import psutil
from fastapi import FastAPI

app = FastAPI()
_PROC = psutil.Process()
tracemalloc.start(5)        # keep 5 frames of allocation traceback

# THE LEAK: every request appends here and nothing is ever removed.
_LEAKED: list = []


class Widget:
    """A small object we deliberately accumulate to simulate a leak."""
    def __init__(self, i: int):
        self.i = i
        self.payload = [i] * 1000   # ~8 KB each, so the leak is visible in RSS


@app.get("/leak")
def leak(n: int = 1000):
    """Allocate n Widgets and 'forget' to free them (append to a global)."""
    _LEAKED.extend(Widget(i) for i in range(n))
    return {"leaked_now": n, "total_held": len(_LEAKED)}


@app.get("/healthy")
def healthy(n: int = 1000):
    """Allocate n Widgets but drop them — a non-leaking endpoint for contrast."""
    tmp = [Widget(i) for i in range(n)]
    return {"created_and_freed": len(tmp)}


@app.get("/_memory")
def memory():
    """Dozer-style introspection: RSS + object-type counts + allocation sites."""
    rss_mb = round(_PROC.memory_info().rss / 1024 / 1024, 1)
    widgets = sum(1 for o in gc.get_objects() if isinstance(o, Widget))
    top_types = objgraph.most_common_types(limit=6)          # [(name, count), ...]
    snap = tracemalloc.take_snapshot()
    top_alloc = [
        f"{s.size // 1024} KiB  {s.traceback[0]}"
        for s in snap.statistics("lineno")[:4]
    ]
    return {
        "rss_mb": rss_mb,
        "live_Widget_objects": widgets,
        "top_object_types": top_types,
        "top_allocations": top_alloc,
    }
