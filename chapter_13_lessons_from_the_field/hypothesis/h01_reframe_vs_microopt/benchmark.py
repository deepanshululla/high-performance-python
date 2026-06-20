"""h01 — does an algorithmic reframe beat line-level micro-optimization by an order of magnitude?

David Rawlinson's headline claim: "optimization of a defined, efficiently implemented
computational process tends to give speedups that are about one order of magnitude (say, 2 to
10 times), whereas new ideas and approaches are more likely to enable 10 or 100 times speedups."
Alex Kelly's Smesh story says the same from the trenches: tuning the regexes gave only "a small
increase," while reframing the problem with Aho-Corasick gave the order of magnitude.

HYPOTHESIS: on one fixed task — match a stream of tweets against K keyword patterns — *tuning the
implementation* without changing the algorithm yields only a small (single-digit) speedup, while
*changing the algorithm* yields an order of magnitude or more.

Four rungs, all returning identical matches per tweet (the correctness anchor):

  1. naive    — compile K regexes, run all K against every tweet. The baseline (already O(N*K)).
  2. tuned    — the genuine line-level micro-optimization: hoist bound .search methods into a
                local list, drop the dict lookup, tighten the loop. Same O(N*K) algorithm.
  3. combined — fold all K patterns into ONE alternation regex. This LOOKS like an
                implementation tweak but is secretly algorithmic: Python's re engine scans the
                literal alternation in roughly one pass instead of K.
  4. reframe  — an explicit Aho-Corasick automaton scans each tweet once for all literals, then
                only the flagged regexes run.

PREDICTION: `tuned` stays in the low single digits (Rawlinson's "2-10x" band, if that); both
`combined` and `reframe` clear 10x by changing the algorithm. The instructive twist is that the
one-liner (`combined`) belongs in the algorithmic band, not the tuning band — so the partition is
about *what changes algorithmically*, not how many lines you touch.
"""
import pathlib
import random
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))   # repo root -> perf

import ahocorasick  # noqa: E402

from perf import time_s  # noqa: E402

N_KEYWORDS = 600
N_TWEETS = 1000
WORDS_PER_TWEET = 18
KEYWORD_DENSITY = 0.15

LABELS = ["naive", "tuned", "combined", "reframe"]
# Which rungs change the algorithm vs merely tune the implementation.
KIND = {"naive": "baseline", "tuned": "micro-opt", "combined": "algorithmic", "reframe": "algorithmic"}


def _make_data(seed=0):
    rng = random.Random(seed)
    filler = [f"word{i}" for i in range(3000)]
    keywords = [f"kw{i}term" for i in range(N_KEYWORDS)]
    tweets = []
    for _ in range(N_TWEETS):
        toks = [rng.choice(filler) for _ in range(WORDS_PER_TWEET)]
        if rng.random() < KEYWORD_DENSITY:
            kw = rng.choice(keywords)
            prefix = rng.choice(["", "", "#", "@"])
            toks[rng.randrange(len(toks))] = prefix + kw
        tweets.append(" ".join(toks))
    return keywords, tweets


def match_naive(tweets, patterns):
    """Baseline: dict of compiled regexes, test all K per tweet."""
    items = list(patterns.items())
    return [{kw for kw, rx in items if rx.search(t)} for t in tweets]


def match_tuned(tweets, searches):
    """Genuine micro-opt: pre-bound .search methods in a flat list, tight loop. Still O(N*K)."""
    out = []
    for t in tweets:
        hits = set()
        for kw, search in searches:
            if search(t):
                hits.add(kw)
        out.append(hits)
    return out


def match_combined(tweets, combined):
    """One alternation regex per tweet — a one-liner that is algorithmic under the hood."""
    return [set(combined.findall(t)) for t in tweets]


def match_reframe(tweets, patterns, automaton):
    out = []
    for t in tweets:
        candidates = {kw for _, kw in automaton.iter(t)}
        out.append({kw for kw in candidates if patterns[kw].search(t)})
    return out


def run(seed=0):
    keywords, tweets = _make_data(seed)
    patterns = {kw: re.compile(rf"(?<!\w)[#@]?{re.escape(kw)}(?!\w)") for kw in keywords}
    searches = [(kw, rx.search) for kw, rx in patterns.items()]
    combined = re.compile(rf"(?<!\w)[#@]?({'|'.join(re.escape(k) for k in keywords)})(?!\w)")
    automaton = ahocorasick.Automaton()
    for kw in keywords:
        automaton.add_word(kw, kw)
    automaton.make_automaton()

    a = match_naive(tweets, patterns)
    b = match_tuned(tweets, searches)
    c = match_combined(tweets, combined)
    d = match_reframe(tweets, patterns, automaton)
    assert a == b == c == d, "a path disagreed with the naive baseline!"

    times = {
        "naive": time_s(lambda: match_naive(tweets, patterns), number=1, repeat=3),
        "tuned": time_s(lambda: match_tuned(tweets, searches), number=1, repeat=3),
        "combined": time_s(lambda: match_combined(tweets, combined), number=1, repeat=3),
        "reframe": time_s(lambda: match_reframe(tweets, patterns, automaton), number=1, repeat=3),
    }
    speedups = {k: times["naive"] / v for k, v in times.items()}
    # CONFIRMED if genuine tuning stays small (<10x) while the algorithmic rungs clear 10x.
    confirmed = (speedups["tuned"] < 10
                 and speedups["combined"] >= 10
                 and speedups["reframe"] >= 10)
    return {"times": times, "speedups": speedups, "confirmed": confirmed}


def main():
    r = run()
    print(f"matching {N_TWEETS:,} tweets against {N_KEYWORDS} keyword patterns:\n")
    for name in LABELS:
        print(f"  {name:9} [{KIND[name]:10}]: {r['times'][name]*1e3:8.2f} ms   "
              f"{r['speedups'][name]:9.1f}x vs naive")
    print(f"\n  genuine tuning (tuned)     : {r['speedups']['tuned']:.1f}x  (implementation only)")
    print(f"  algorithmic, one-liner     : {r['speedups']['combined']:,.0f}x  (combined regex)")
    print(f"  algorithmic, explicit      : {r['speedups']['reframe']:,.0f}x  (Aho-Corasick)")
    verdict = "CONFIRMED" if r["confirmed"] else "OVERTURNED"
    print(f"\n  VERDICT: {verdict} — tuning stays in the low single digits; the "
          f"order-of-magnitude wins all come from changing the algorithm")


if __name__ == "__main__":
    main()
