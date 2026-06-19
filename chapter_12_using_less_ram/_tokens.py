"""Reproducible token datasets for the text-container exercises.

The book's trie story uses 12.5 million unique Wikipedia tokens, a 120 MB file we
don't ship. We generate a deterministic stand-in instead, with one important knob
that the book's prose keeps returning to: *how much structure the strings share*.
A trie only compresses what it can fold together, so we expose two distributions
of equal-length tokens that differ only in their front structure:

* ``"prefixed"`` — every token starts with one of a small pool of shared prefixes
  ("inter", "under", "trans", ...), like natural-language vocabulary. A trie folds
  those shared fronts into single branches, which is where its RAM win comes from.
* ``"random"`` — fixed-length hex strings with essentially no shared structure.
  Two tokens almost never share even a leading character, so a trie has nothing to
  fold and degenerates toward storing every string in full.

Both streams are **unique by construction** and produced by a generator that holds
no state proportional to ``n`` — critical for the memory exercises, where a dedup
``set`` kept alongside the container under test would double-count its cost. Holding
the token length equal across both distributions keeps the comparison fair: any RAM
difference is attributable to shared structure, not string size. This is the lever
the chapter's hypothesis pulls (``hypothesis/h01_trie_needs_prefixes``).
"""
import hashlib

# A pool of word-like prefixes; natural English vocabulary shares fronts like these.
PREFIXES = [
    "inter", "under", "trans", "super", "hyper", "micro", "macro", "multi",
    "proto", "pseudo", "quasi", "anti", "auto", "counter", "extra", "ultra",
    "over", "semi", "sub", "non", "pre", "post", "redo", "deco", "disco",
    "miso", "outer", "para", "meta", "poly", "mono", "unim", "omni", "neon",
]
TOKEN_LEN = 16          # total characters per token, held equal across distributions
KNOWN_TOKEN = "interPRESENT0000"   # guaranteed-present probe (shares a real prefix)


def token_stream(n, kind="prefixed", seed=0):
    """Yield ``n`` unique tokens of the chosen distribution, in O(1) memory.

    The last token yielded is always ``KNOWN_TOKEN`` so lookups have a definite hit.
    No per-element state is retained, so a caller can build *one* container from the
    stream and measure exactly that container's footprint.
    """
    salt = str(seed)
    if kind == "prefixed":
        npre = len(PREFIXES)
        for i in range(n - 1):
            pre = PREFIXES[i % npre]
            tail = format(i, "x")              # hex of the index — unique per i
            yield (pre + tail).ljust(TOKEN_LEN, "0")[:TOKEN_LEN]
    elif kind == "random":
        for i in range(n - 1):
            h = hashlib.blake2b(f"{salt}:{i}".encode(), digest_size=8).hexdigest()
            yield h[:TOKEN_LEN]                 # 16 hex chars, ~no shared prefix
    else:
        raise ValueError(f"unknown kind {kind!r}")
    yield KNOWN_TOKEN


def make_tokens(n, kind="prefixed", seed=0):
    """Materialise ``token_stream`` into a list (for lookup-timing, not RAM sizing)."""
    return list(token_stream(n, kind, seed))
