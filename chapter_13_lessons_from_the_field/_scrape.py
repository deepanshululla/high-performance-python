"""A local stand-in for an ISP "internet plan lookup" website, for ex01.

Leon Yin's chapter describes scraping internet-plan prices for over a million
addresses. A Selenium scraper that drives a real browser managed ~300 addresses a
day; replaying the site's *undocumented internal API* with a `requests.Session`
(and then fanning the calls out asynchronously) reached ~300,000 a day — a
roughly 1000x jump. We obviously can't hit a real ISP here, so this module stands
up a small local server that reproduces the two cost structures the story turns on:

  * `/page/<addr>`  — the "browser" path. Returns a large HTML document (a few
    hundred KB of markup with the plan data buried inside it) and sleeps long
    enough to model the cascade of sub-resource requests a browser serialises
    while rendering a page. This is what Selenium effectively pays per address.

  * `/authenticate`, `/autocomplete`, `/plans` — the "API" path. The same multi-
    step flow the site's own front-end JavaScript calls: authenticate (sets a
    session cookie), look the address up to get an id, then POST the id to fetch a
    small JSON payload of plans. Each call is cheap and tiny, and the cookie set by
    `/authenticate` is *required* by the later calls — exactly the state a
    `requests.Session` keeps for you automatically.

Both paths return the *same* plan data for a given address, so a scraper can be
checked for correctness against the other. The server runs in a background thread
with its own asyncio loop so a synchronous `requests` client and an async
`aiohttp` client can both hit it from the main thread.
"""
import asyncio
import threading

from aiohttp import web

# One round-trip's worth of artificial latency. Real wide-area requests are tens
# of ms; we keep it small so the suite runs quickly, but large enough that the
# serial-vs-async and one-call-vs-many-calls differences are visible above noise.
BASE_DELAY_S = 0.006

# A browser rendering a page fires many sub-requests (CSS, JS bundles, fonts,
# images, XHRs) and blocks on them; we model that as the page endpoint being this
# many round-trips "deep" before it can answer.
PAGE_SUBRESOURCES = 8

# Roughly how much markup a real plan-lookup page weighs, minus images. The point
# is that the browser path moves hundreds of KB per address while the API path
# moves a few hundred bytes of JSON.
PAGE_PADDING_BYTES = 250_000


def plans_for(address: str):
    """Deterministic 'internet plans' for an address — the data both paths return."""
    seed = sum(ord(c) for c in address)
    speeds = [25, 100, 300, 1000]
    speed = speeds[seed % len(speeds)]
    return {"address": address, "download_mbps": speed, "price_usd": 55}


def _build_app():
    app = web.Application()
    # The browser path: heavy HTML, modelled sub-resource cascade, no session needed.
    padding = "<div class='ad'>x</div>" * (PAGE_PADDING_BYTES // 23)

    async def page(request):
        addr = request.match_info["addr"]
        await asyncio.sleep(BASE_DELAY_S * PAGE_SUBRESOURCES)
        p = plans_for(addr)
        html = (
            "<html><head><title>Internet plans</title></head><body>"
            f"{padding}"
            # The data a browser scraper would dig out of the rendered DOM:
            f"<span id='dl'>{p['download_mbps']}</span>"
            f"<span id='price'>{p['price_usd']}</span>"
            "</body></html>"
        )
        return web.Response(text=html, content_type="text/html")

    # The API path: the site's own three-step internal flow.
    async def authenticate(request):
        await asyncio.sleep(BASE_DELAY_S)
        resp = web.json_response({"ok": True})
        resp.set_cookie("session", "tok-abc123")  # the cookie the later calls need
        return resp

    async def autocomplete(request):
        if request.cookies.get("session") != "tok-abc123":
            return web.json_response({"error": "no session"}, status=401)
        await asyncio.sleep(BASE_DELAY_S)
        addr = request.query.get("address", "")
        return web.json_response({"address_id": addr})

    async def plans(request):
        if request.cookies.get("session") != "tok-abc123":
            return web.json_response({"error": "no session"}, status=401)
        await asyncio.sleep(BASE_DELAY_S)
        body = await request.json()
        return web.json_response(plans_for(body["addressId"]))

    app.router.add_get("/page/{addr}", page)
    app.router.add_get("/authenticate", authenticate)
    app.router.add_get("/autocomplete", autocomplete)
    app.router.add_post("/plans", plans)
    return app


class running_server:
    """Context manager: start the app in a background thread, yield its base URL.

        with running_server() as base:
            requests.get(f"{base}/authenticate")
    """

    def __enter__(self):
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=10)
        return self.base

    def _serve(self):
        asyncio.set_event_loop(self._loop)
        app = _build_app()
        runner = web.AppRunner(app)
        self._loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, "127.0.0.1", 0)
        self._loop.run_until_complete(site.start())
        # Port 0 -> the OS picks a free port; read it back off the bound socket.
        sock = list(site._server.sockets)[0]
        self.base = f"http://127.0.0.1:{sock.getsockname()[1]}"
        self._runner = runner
        self._ready.set()
        self._loop.run_forever()

    def __exit__(self, *exc):
        # Drain in-flight connections before stopping, or aiohttp logs "Task was
        # destroyed but it is pending" for every keep-alive socket still open.
        async def _shutdown():
            await self._runner.cleanup()
            self._loop.stop()

        self._loop.call_soon_threadsafe(lambda: self._loop.create_task(_shutdown()))
        self._thread.join(timeout=5)
        return False
