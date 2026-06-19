"""ex01 — why replaying an API with a session (then going async) beat a browser ~1000x.

Leon Yin's investigation scraped internet-plan prices for a million-plus addresses. A
Selenium scraper driving a real browser managed ~300 addresses/day; replaying the site's
own internal JSON API with a `requests.Session`, then fanning the calls out asynchronously,
reached ~300,000/day. This drill reproduces the *shape* of that result against a local
server (`_scrape.py`) that mimics the two cost structures:

  1. Browser path — download a heavy HTML page per address (hundreds of KB) whose render
     blocks on a cascade of sub-resource round-trips, then dig the data out of the markup.
     One fresh connection per address, done serially. This is what Selenium pays.
  2. Session API, serial — one `requests.Session` walks the site's three-step flow
     (authenticate → autocomplete → plans). The session keeps the auth cookie the later
     calls require and reuses the TCP connection. Tiny JSON payloads.
  3. Async API — the same three-step flow per address, but with an `aiohttp` session
     fanning all the addresses out concurrently so the network waits overlap.

All three must extract the *same* plans for the same addresses (the correctness anchor),
so a faster path can't win by returning garbage. We report addresses/second for each.
"""
import asyncio
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root -> perf
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir -> _scrape

import aiohttp  # noqa: E402
import requests  # noqa: E402

from _scrape import plans_for, running_server  # noqa: E402

N_ADDRESSES = 60
ADDRESSES = [f"{n} Main St" for n in range(N_ADDRESSES)]

_DL = re.compile(r"id='dl'>(\d+)<")
_PRICE = re.compile(r"id='price'>(\d+)<")


def scrape_browser(base, addresses):
    """Serial, one fresh connection per address, full-page download + HTML parse."""
    out = {}
    for addr in addresses:
        # requests.get with no Session: a new connection pool each call (no reuse).
        html = requests.get(f"{base}/page/{addr}").text
        out[addr] = {
            "address": addr,
            "download_mbps": int(_DL.search(html).group(1)),
            "price_usd": int(_PRICE.search(html).group(1)),
        }
    return out


def scrape_session(base, addresses):
    """Serial, one Session: cookie + connection reused across the 3-step API flow."""
    out = {}
    with requests.Session() as s:
        s.get(f"{base}/authenticate")          # sets the session cookie once
        for addr in addresses:
            r = s.get(f"{base}/autocomplete", params={"address": addr})
            address_id = r.json()["address_id"]
            out[addr] = s.post(f"{base}/plans", json={"addressId": address_id}).json()
    return out


async def _one_async(session, base, addr):
    async with session.get(f"{base}/autocomplete", params={"address": addr}) as r:
        address_id = (await r.json())["address_id"]
    async with session.post(f"{base}/plans", json={"addressId": address_id}) as r:
        return addr, await r.json()


async def _scrape_async(base, addresses):
    # unsafe=True so the cookie jar keeps cookies set by an IP-address host (127.0.0.1);
    # the default jar silently drops them, exactly as a browser would for a bare IP.
    jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        async with session.get(f"{base}/authenticate"):
            pass                                # cookie is stored on the session
        tasks = [_one_async(session, base, a) for a in addresses]
        return dict(await asyncio.gather(*tasks))


def scrape_async(base, addresses):
    return asyncio.run(_scrape_async(base, addresses))


def measure(addresses=ADDRESSES):
    """Run all three scrapers against a fresh local server; return rates + speedups."""
    import time

    expected = {a: plans_for(a) for a in addresses}
    out = {}
    with running_server() as base:
        for name, fn in (("browser", scrape_browser),
                         ("session", scrape_session),
                         ("async", scrape_async)):
            t0 = time.perf_counter()
            got = fn(base, addresses)
            dt = time.perf_counter() - t0
            assert got == expected, f"{name} extracted the wrong plans!"
            out[name] = {"seconds": dt, "rate": len(addresses) / dt}
    return out


def main():
    m = measure()
    print(f"scraping {N_ADDRESSES} addresses three ways:\n")
    base_rate = m["browser"]["rate"]
    for name in ("browser", "session", "async"):
        d = m[name]
        print(f"  {name:8}: {d['seconds']:6.3f}s   {d['rate']:8.1f} addr/s   "
              f"{d['rate'] / base_rate:6.1f}x vs browser")


if __name__ == "__main__":
    main()
