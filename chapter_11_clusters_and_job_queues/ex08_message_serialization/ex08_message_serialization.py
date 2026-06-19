"""ex08 — how to serialize a message: JSON vs pickle vs msgpack.

Every message a cluster sends has to be turned into bytes and back. The book has
a strong and slightly counterintuitive recommendation here: *prefer human-readable
text (JSON) over a low-level compressed binary protocol*, even though the binary
form is faster and smaller. The reasoning is operational, not performance: "when
you're left with a partial database after a core computer has caught fire, you'll
be glad that you can read the important messages quickly as you work to bring the
system back online." Debuggability beats a few saved bytes.

This exercise puts numbers on what that recommendation costs, so you can make the
trade with your eyes open. We take one representative message — a "user rated an
item" event, the book's own queue example, with nested context, a list of recent
items, and some tags — and serialize it three ways:

  * **JSON** (`json`) — human-readable UTF-8 text, language-agnostic, the book's
    pick. You can `cat` it and read it.
  * **msgpack** (`msgpack`) — a compact binary encoding that is still
    language-agnostic (clients exist for every major language). Not human-readable.
  * **pickle** (`pickle`) — Python's native binary format. Fast and compact, but
    Python-only *and a security risk*: unpickling untrusted data can execute
    arbitrary code, so it must never cross a trust boundary.

We measure encode time, decode time, and the serialized size of each, and verify
every codec round-trips to the identical object.
"""
import json
import pathlib
import pickle
import sys

import msgpack

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from perf import time_s, human  # noqa: E402

NUMBER = 20_000        # encode/decode repetitions per timing sample


def sample_message():
    """One representative cluster message: the book's 'user rated an item' event."""
    return {
        "event": "user.rated.item",
        "user_id": 184213,
        "item_id": 99821,
        "rating": 4.5,
        "timestamp": "2026-06-18T12:34:56Z",
        "context": {"device": "ios", "app_version": "7.2.1", "ab_bucket": 7,
                    "session": "a1b2c3d4e5f6a7b8c9d0"},
        "recent_items": [99821 - i * 37 for i in range(20)],
        "tags": ["sci-fi", "thriller", "space", "dystopia", "classic"],
    }


CODECS = {
    "json":    (lambda o: json.dumps(o).encode("utf-8"), lambda b: json.loads(b)),
    "msgpack": (lambda o: msgpack.packb(o, use_bin_type=True),
                lambda b: msgpack.unpackb(b, raw=False)),
    "pickle":  (lambda o: pickle.dumps(o, protocol=pickle.HIGHEST_PROTOCOL),
                lambda b: pickle.loads(b)),
}


def measure():
    msg = sample_message()
    out = {}
    for name, (enc, dec) in CODECS.items():
        raw = enc(msg)
        assert dec(raw) == msg, f"{name} did not round-trip to the identical object"
        enc_s = time_s(lambda: enc(msg), number=NUMBER, repeat=5)
        dec_s = time_s(lambda: dec(raw), number=NUMBER, repeat=5)
        out[name] = {"size": len(raw), "encode_us": enc_s * 1e6, "decode_us": dec_s * 1e6,
                     "readable": name == "json", "portable": name != "pickle"}
    return out


def main():
    out = measure()
    js = out["json"]
    print("serializing one representative message, three ways:")
    print(f"  {'codec':<9}{'size':>8}{'encode':>11}{'decode':>11}  notes")
    for name, s in out.items():
        notes = []
        notes.append("human-readable" if s["readable"] else "binary")
        notes.append("any language" if s["portable"] else "Python-only, unsafe on untrusted input")
        print(f"  {name:<9}{human(s['size']):>8}{s['encode_us']:>9.1f}us{s['decode_us']:>9.1f}us  "
              f"{', '.join(notes)}")
    best = min(out, key=lambda n: out[n]["size"])
    print(f"  smallest: {best} ({out[best]['size']}B vs json {js['size']}B = "
          f"{js['size']/out[best]['size']:.2f}x bigger for JSON)")
    fast = min(out, key=lambda n: out[n]["encode_us"] + out[n]["decode_us"])
    js_rt = js["encode_us"] + js["decode_us"]
    fast_rt = out[fast]["encode_us"] + out[fast]["decode_us"]
    print(f"  fastest round-trip: {fast} ({fast_rt:.1f}us vs json {js_rt:.1f}us = "
          f"{js_rt/fast_rt:.2f}x slower for JSON)")
    print("  JSON pays size and speed for the one thing the book values most: you can read it")


if __name__ == "__main__":
    main()
