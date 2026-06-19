"""h01 — Does a trie's RAM win over a set come from shared prefixes?

ex05 showed a loaded marisa_trie costing ~57x less RAM than a `set` of the same two
million tokens. But the book is careful to say the trie's benefit "depends on your
data's structure" — a trie compresses by folding *shared prefixes* into single branches,
so its advantage should evaporate on data with no shared structure.

HYPOTHESIS: the trie's RAM advantage over a set is largely due to shared prefixes. On
high-entropy random tokens (16 hex characters, almost never sharing even a leading
character) the trie has nothing to fold, so its advantage over a set should shrink
dramatically compared to the prefix-heavy case.

We hold everything else equal — same token count, same 16-character length, same
structures — and only change the token distribution (``"prefixed"`` vs ``"random"``,
from ``_tokens.py``). We measure the loaded-trie and set footprints (peak RSS in a fresh
process) for each distribution and compare the advantage ratios. The verdict is
data-driven: if the random-token advantage is much smaller than the prefixed-token one,
the hypothesis is CONFIRMED.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))   # repo root
sys.path.insert(0, str(HERE.parents[1]))   # chapter dir -> _mem, _tokens

import marisa_trie  # noqa: E402

from _mem import peak_rss_mib  # noqa: E402
from _tokens import token_stream  # noqa: E402

N = 2_000_000
KINDS = ["prefixed", "random"]


def _trie_path(kind):
    return HERE / f"tokens_{kind}.marisa"


def build_set(kind, n=N):
    return set(token_stream(n, kind))


def build_trie_and_save(kind, n=N):
    t = marisa_trie.Trie(token_stream(n, kind))
    t.save(str(_trie_path(kind)))
    return t


def load_trie(kind):
    return marisa_trie.Trie().load(str(_trie_path(kind)))


def run(n=N):
    out = {}
    for kind in KINDS:
        build_trie_and_save(kind, n)                     # persist for the load measurement
        set_mib = peak_rss_mib(build_set, kind, n)
        trie_mib = peak_rss_mib(load_trie, kind)
        out[kind] = {"set_mib": set_mib, "trie_mib": trie_mib,
                     "advantage": set_mib / trie_mib}
    pref_adv = out["prefixed"]["advantage"]
    rand_adv = out["random"]["advantage"]
    # CONFIRMED if shared prefixes account for most of the advantage: the random-token
    # advantage should be a small fraction of the prefixed-token advantage.
    shrink = pref_adv / rand_adv
    confirmed = rand_adv < pref_adv / 2
    return {"by_kind": out, "pref_adv": pref_adv, "rand_adv": rand_adv,
            "shrink": shrink, "confirmed": confirmed}


def main():
    r = run()
    print(f"trie vs set RAM for {N:,} tokens, by distribution "
          f"(RAM = peak RSS in a fresh process):\n")
    print(f"  {'distribution':12} {'set MiB':>9} {'trie MiB':>9} {'trie advantage':>16}")
    for kind in KINDS:
        d = r["by_kind"][kind]
        print(f"  {kind:12} {d['set_mib']:9.1f} {d['trie_mib']:9.1f} "
              f"{d['advantage']:14.1f}x")
    verdict = "CONFIRMED" if r["confirmed"] else "OVERTURNED"
    print(f"\n  prefixed advantage {r['pref_adv']:.1f}x vs random advantage "
          f"{r['rand_adv']:.1f}x  ->  shrinks {r['shrink']:.1f}x")
    print(f"  VERDICT: {verdict} — the trie's RAM win is "
          f"{'largely' if r['confirmed'] else 'NOT mainly'} due to shared prefixes.")


if __name__ == "__main__":
    main()
