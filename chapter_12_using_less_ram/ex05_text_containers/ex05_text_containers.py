"""ex05 — storing millions of strings: list, sorted+bisect, set, dict, and a trie.

This is the chapter's set-piece (the book's Figure 12-2). We hold the same large pool
of unique tokens in five containers and ask two questions of each: how much RAM does it
cost, and how fast can we check whether a known token is present?

* a plain `list` with a linear `in` scan — O(n) per lookup, ruinously slow at scale;
* the same list `sort`ed once and queried with `bisect` — O(log n), the fair baseline;
* a `set` — hashed, fast lookups, but each string stored separately with table overhead;
* a `dict` mapping token to index — like the set plus a value per key;
* a `marisa_trie.Trie`, which folds shared prefixes into a compressed structure, then is
  saved to disk and reloaded — the build-once / load-many pattern where it shines.

RAM is measured as peak RSS in a fresh process (see `_mem.py`); the containers are built
straight from a streaming generator so we weigh the container and its strings, not a stray
token list. Lookups are timed in-process on a prebuilt container. The trie is measured
twice — at build time (which transiently holds the source strings, so it looks large) and
loaded from disk in a clean process (the real, tiny footprint).
"""
import bisect
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root -> perf
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir -> _mem, _tokens

import marisa_trie  # noqa: E402

from _mem import peak_rss_mib  # noqa: E402
from _tokens import KNOWN_TOKEN, make_tokens, token_stream  # noqa: E402
from perf import time_s  # noqa: E402

N = 2_000_000          # unique tokens (scaled down from the book's 12.5M)
KIND = "prefixed"      # natural-language-like shared prefixes — trie-friendly
TRIE_PATH = HERE / "tokens.marisa"

# ---- builders (each consumes the generator so only the container retains strings) ----

def build_list(n=N):
    return list(token_stream(n, KIND))


def build_set(n=N):
    return set(token_stream(n, KIND))


def build_dict(n=N):
    return {tok: i for i, tok in enumerate(token_stream(n, KIND))}


def build_trie(n=N):
    return marisa_trie.Trie(token_stream(n, KIND))


def build_trie_and_save(n=N):
    """Build the trie and persist it, so a later process can load it cheaply."""
    t = marisa_trie.Trie(token_stream(n, KIND))
    t.save(str(TRIE_PATH))
    return t


def load_trie():
    return marisa_trie.Trie().load(str(TRIE_PATH))


# ---- measurement ----------------------------------------------------------------------

def measure(n=N):
    """Return {container: {rss_mib, build_s, lookup_us}} plus the trie load row."""
    # Make sure the saved trie exists on disk for the load measurement.
    build_trie_and_save(n)

    rss = {
        "list": peak_rss_mib(build_list, n),
        "set": peak_rss_mib(build_set, n),
        "dict": peak_rss_mib(build_dict, n),
        "trie (build)": peak_rss_mib(build_trie, n),
        "trie (load)": peak_rss_mib(load_trie),
    }

    # Build once in-process for build-time and lookup timing.
    out = {}
    tokens = make_tokens(n, KIND)

    t0 = time_s(lambda: build_list(n), number=1, repeat=1)
    lst = list(tokens)
    # linear scan: O(n), so we time a handful of hits, not the book's 100k.
    lin = time_s(lambda: KNOWN_TOKEN in lst, number=1, repeat=3)
    out["list (linear)"] = {"rss_mib": rss["list"], "build_s": t0, "lookup_us": lin * 1e6}

    srt = sorted(lst)
    t_sort = time_s(lambda: sorted(lst), number=1, repeat=1)
    bis = time_s(lambda: _bisect_has(srt, KNOWN_TOKEN), number=1000, repeat=5)
    out["list+bisect"] = {"rss_mib": rss["list"], "build_s": t0 + t_sort,
                          "lookup_us": bis * 1e6}

    t_set = time_s(lambda: build_set(n), number=1, repeat=1)
    s = set(tokens)
    set_lk = time_s(lambda: KNOWN_TOKEN in s, number=1000, repeat=5)
    out["set"] = {"rss_mib": rss["set"], "build_s": t_set, "lookup_us": set_lk * 1e6}

    t_dict = time_s(lambda: build_dict(n), number=1, repeat=1)
    d = {tok: i for i, tok in enumerate(tokens)}
    d_lk = time_s(lambda: KNOWN_TOKEN in d, number=1000, repeat=5)
    out["dict"] = {"rss_mib": rss["dict"], "build_s": t_dict, "lookup_us": d_lk * 1e6}

    t_trie = time_s(lambda: build_trie(n), number=1, repeat=1)
    tr = load_trie()
    assert KNOWN_TOKEN in tr, "known token missing from trie!"
    tr_lk = time_s(lambda: KNOWN_TOKEN in tr, number=1000, repeat=5)
    out["trie (build)"] = {"rss_mib": rss["trie (build)"], "build_s": t_trie,
                           "lookup_us": tr_lk * 1e6}
    out["trie (load)"] = {"rss_mib": rss["trie (load)"], "build_s": 0.0,
                          "lookup_us": tr_lk * 1e6}
    return out


def _bisect_has(sorted_list, x):
    i = bisect.bisect_left(sorted_list, x)
    return i != len(sorted_list) and sorted_list[i] == x


def main():
    m = measure()
    print(f"{N:,} unique {KIND} tokens in five containers "
          f"(RAM = peak RSS in a fresh process):\n")
    print(f"  {'container':14} {'RAM (MiB)':>10} {'build (s)':>10} {'lookup':>12}")
    for name, d in m.items():
        lk = (f"{d['lookup_us']/1e6:.4f} s" if d["lookup_us"] > 1e5
              else f"{d['lookup_us']:.3f} us")
        print(f"  {name:14} {d['rss_mib']:10.1f} {d['build_s']:10.2f} {lk:>12}")
    set_rss = m["set"]["rss_mib"]
    trie_rss = m["trie (load)"]["rss_mib"]
    print(f"\n  trie (loaded) vs set RAM: {set_rss/trie_rss:.1f}x smaller — shared "
          f"prefixes folded away. The linear-scan list is the slow trap.")


if __name__ == "__main__":
    main()
