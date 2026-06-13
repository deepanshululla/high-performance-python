"""The shared workload every Chapter 9 exercise runs, so the numbers line up.

Two pieces, mirroring the chapter's two running examples:

1. `generate_urls(base, n)` — the crawler target. We append random characters to each URL so
   neither the client library nor the server can serve a cached response; every request pays
   the full round-trip the `delay` parameter dictates.

2. `do_task(difficulty)` — the CPU half of the CPU+I/O workload. It bcrypt-hashes a random
   string at a chosen cost factor. bcrypt is deliberately, tunably slow (that's its job as a
   password hash), which makes it a clean knob for "how much CPU work sits between two I/O
   calls." The chapter's Table 9-1 lists ~17 ms/iter at difficulty 8 on the book's machine.

`URL_DELAY_MS` and the scaled iteration counts live here too, in one place, so a change to the
workload size touches every exercise at once. They are *scaled down* from the book (which uses
1000 requests / 600 hashes at 100 ms) to keep the whole suite runnable in seconds rather than
minutes — the ratios between serial/batched/async are the lesson, not the absolute seconds.
"""
import random
import string

import bcrypt

# Shared knobs. Scaled to keep the suite fast; see module docstring.
URL_DELAY_MS = 50          # per-request server delay (book uses 100)
N_REQUESTS = 200           # crawler request count (book uses 1000)
N_HASHES = 120             # CPU+I/O iteration count (book uses 600)
DEFAULT_DIFFICULTY = 8     # bcrypt cost factor (book's headline difficulty)
DEFAULT_CONCURRENCY = 100  # simultaneous-connection cap (aiohttp's own default)


def generate_urls(base_url: str, num_urls: int):
    """Yield `num_urls` cache-busting URLs against the server's /get endpoint."""
    for _ in range(num_urls):
        suffix = "".join(random.sample(string.ascii_lowercase, 10))
        sep = "&" if "?" in base_url else "?"
        yield f"{base_url}{sep}cb={suffix}"


def do_task(difficulty: int = DEFAULT_DIFFICULTY) -> str:
    """bcrypt-hash a random 10-char string at the given cost factor; return the hash text."""
    passwd = "".join(random.sample(string.ascii_lowercase, 10)).encode("utf8")
    salt = bcrypt.gensalt(difficulty)
    return bcrypt.hashpw(passwd, salt).decode("utf8")
