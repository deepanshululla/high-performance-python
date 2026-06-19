"""ex02 — an Aho-Corasick prefilter beats running every regex on every tweet.

Smesh streamed hundreds of tweets a second and matched each against hundreds-to-thousands
of tracked keywords. The matching wasn't plain substring search — they needed word
boundaries and optional `#`/`@` prefixes — so regexes were the natural tool. But running
thousands of regexes against every tweet was the bottleneck, and micro-optimising the
regexes only shaved fractions. The fix was to *reduce the problem space first*: an
Aho-Corasick automaton scans each tweet once and reports which keyword literals appear at
all, so only that handful of candidate regexes need to run. They reported a 10-100x speedup.

This drill reproduces that. We build a few thousand keyword regexes (each enforcing word
boundaries and an optional `#`/`@` prefix), stream synthetic tweets, and match two ways:

  * brute force — run all K compiled regexes against every tweet (N x K searches);
  * Aho-Corasick prefilter — scan the tweet once for keyword literals, then run only the
    regexes whose literal actually appeared.

Aho-Corasick is a *sound* prefilter: a keyword's regex can only match if its literal is in
the text, so the automaton never misses a real match (it can over-suggest — `python` inside
`pythonic` — but the regex makes the final call). We assert the two paths agree per tweet.
"""
import pathlib
import random
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root -> perf

import ahocorasick  # noqa: E402

from perf import time_s  # noqa: E402

N_KEYWORDS = 600
N_TWEETS = 1000
WORDS_PER_TWEET = 18
KEYWORD_DENSITY = 0.15   # fraction of tweets that actually contain a tracked keyword


def _make_data(seed=0):
    rng = random.Random(seed)
    # A pool of "ordinary" words plus the tracked keywords; keywords are rare in the stream.
    filler = [f"word{i}" for i in range(3000)]
    keywords = [f"kw{i}term" for i in range(N_KEYWORDS)]
    tweets = []
    for _ in range(N_TWEETS):
        toks = [rng.choice(filler) for _ in range(WORDS_PER_TWEET)]
        if rng.random() < KEYWORD_DENSITY:
            kw = rng.choice(keywords)
            prefix = rng.choice(["", "", "#", "@"])  # sometimes a hashtag/mention
            toks[rng.randrange(len(toks))] = prefix + kw
        tweets.append(" ".join(toks))
    return keywords, tweets


def _compile(keywords):
    # Match the keyword on word boundaries, allowing an optional leading # or @.
    return {kw: re.compile(rf"(?<!\w)[#@]?{re.escape(kw)}(?!\w)") for kw in keywords}


def _build_automaton(keywords):
    A = ahocorasick.Automaton()
    for kw in keywords:
        A.add_word(kw, kw)          # value stored at the literal = the keyword itself
    A.make_automaton()
    return A


def match_brute(tweets, patterns):
    """For every tweet, test all K regexes. O(N*K) searches."""
    results = []
    items = list(patterns.items())
    for t in tweets:
        hits = {kw for kw, rx in items if rx.search(t)}
        results.append(hits)
    return results


def match_aho(tweets, patterns, automaton):
    """Scan each tweet once for keyword literals, then confirm only those with their regex."""
    results = []
    for t in tweets:
        candidates = {kw for _, kw in automaton.iter(t)}   # literals present (a superset)
        hits = {kw for kw in candidates if patterns[kw].search(t)}
        results.append(hits)
    return results


def measure(seed=0):
    keywords, tweets = _make_data(seed)
    patterns = _compile(keywords)
    automaton = _build_automaton(keywords)

    brute = match_brute(tweets, patterns)
    aho = match_aho(tweets, patterns, automaton)
    assert brute == aho, "Aho-Corasick prefilter disagreed with brute force!"

    t_brute = time_s(lambda: match_brute(tweets, patterns), number=1, repeat=3)
    t_aho = time_s(lambda: match_aho(tweets, patterns, automaton), number=1, repeat=3)
    n_hits = sum(len(h) for h in brute)
    return {
        "n_keywords": len(keywords), "n_tweets": len(tweets), "n_hits": n_hits,
        "brute_s": t_brute, "aho_s": t_aho, "speedup": t_brute / t_aho,
        "brute_rate": len(tweets) / t_brute, "aho_rate": len(tweets) / t_aho,
    }


def main():
    m = measure()
    print(f"{m['n_tweets']:,} tweets x {m['n_keywords']:,} keyword regexes "
          f"({m['n_hits']:,} matches found):\n")
    print(f"  brute force   : {m['brute_s']:.3f}s  ({m['brute_rate']:8.0f} tweets/s)")
    print(f"  Aho-Corasick  : {m['aho_s']:.3f}s  ({m['aho_rate']:8.0f} tweets/s)")
    print(f"\n  speedup: {m['speedup']:.1f}x")


if __name__ == "__main__":
    main()
