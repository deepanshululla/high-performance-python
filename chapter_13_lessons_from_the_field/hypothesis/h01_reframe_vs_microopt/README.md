# h01 — algorithmic reframe vs line-level micro-optimization

> **Hypothesis:** On one fixed task, *tuning the implementation* without changing the algorithm yields
> only a small (single-digit) speedup, while *changing the algorithm* yields an order of magnitude or
> more. **Verdict: CONFIRMED — and more starkly than the claim states.**

This lab puts a number on the chapter's most quotable cross-cutting claim. David Rawlinson:
"optimization of a defined, efficiently implemented computational process tends to give speedups that
are about one order of magnitude (say, 2 to 10 times), whereas new ideas and approaches are more
likely to enable 10 or 100 times speedups." Alex Kelly's Smesh story is the same lesson from the
field: tuning the regexes bought "a small increase," and the order of magnitude only arrived when they
reframed the matching with Aho-Corasick. So we take Smesh's exact task — match a stream of tweets
against K keyword patterns — and climb four rungs, from baseline to genuine tuning to two algorithmic
reformulations, measuring each against the naive baseline. All four return identical matches per tweet.

## The four rungs

- **naive** — a dict of K compiled regexes, every one tested against every tweet. Already O(N·K).
- **tuned** — the honest line-level micro-optimization: hoist the bound `.search` methods into a flat
  list, drop the dict lookup, tighten the loop. Same O(N·K) algorithm, just a leaner implementation.
- **combined** — fold all K patterns into one alternation regex and scan each tweet with it once. This
  *looks* like an implementation tweak (it's one line) but it changes the algorithm: Python's `re`
  engine scans the literal alternation in roughly a single pass instead of K independent passes.
- **reframe** — an explicit Aho-Corasick automaton scans each tweet once for every keyword literal,
  and only the flagged regexes then run.

## What we found

| rung | kind | time | speedup vs naive |
| --- | --- | ---: | ---: |
| naive | baseline | ~1192 ms | 1.0x |
| tuned | micro-opt | ~1194 ms | **1.0x** |
| combined | algorithmic (one-liner) | ~2.3 ms | **~513x** |
| reframe | algorithmic (explicit) | ~0.7 ms | **~1675x** |

![h01 chart](chart.png)

**Genuine implementation tuning bought nothing — 1.0x, not even Rawlinson's generous lower bound.**
Hoisting bound methods and tightening the loop is exactly the kind of line-level tweak people reach for
first, and here it's *indistinguishable from the baseline*. The reason is instructive: the naive loop
already spends essentially all its time inside the compiled `re` engine, so there's no Python-level
overhead left to shave. When the hot work is already in C, constant-factor tuning of the surrounding
Python is rearranging deck chairs. This is the stronger form of Rawlinson's claim — for an
already-efficient process, "optimization" can give you *zero*, not 2x.

**Both order-of-magnitude wins came from changing the algorithm — and one of them is a one-liner.**
This is the twist that makes the hypothesis worth running. The `combined` rung is a single line of code
that looks like tuning, yet it delivers 513x — because it isn't tuning at all. Python's regex engine
compiles an alternation of literal strings into an efficient scan that finds them in roughly one pass,
so collapsing K regexes into one quietly replaces an O(N·K) algorithm with something close to O(N).
The explicit Aho-Corasick reframe goes further still (1675x) by being a purpose-built multi-pattern
scanner. The lesson the rungs teach together is that **Rawlinson's partition is real, but it's about
what changes algorithmically, not how many lines you touch**: the boundary ran right through the
middle of what looked like a single "optimization," and the order-of-magnitude wins all landed on the
algorithmic side of it.

So the verdict is CONFIRMED on the substance — tuning stayed in the low single digits (here, exactly
1x) while algorithmic change delivered three orders of magnitude — with the refinement that the
*category* of a change ("am I tuning or reframing?") is decided by its effect on the work done, and a
deceptively small edit (one big regex instead of many) can be a reframe in disguise.

## Reading the chart

A single bar chart of speedup over the naive baseline, on a log scale, one bar per rung and coloured by
kind: grey baseline, red for the micro-optimization, teal for the two algorithmic rungs. A dashed line
at 10x marks the boundary between Rawlinson's two bands. The visual story is immediate — the grey and
red bars sit together at the bottom (tuning changed nothing), and both teal bars vault far above the
10x line. Absolute speedups depend on the machine and the keyword count; the durable result is which
side of the 10x line each *kind* of change lands on.

## Run

```bash
.venv/bin/python chapter_13_lessons_from_the_field/hypothesis/h01_reframe_vs_microopt/benchmark.py
.venv/bin/python chapter_13_lessons_from_the_field/hypothesis/h01_reframe_vs_microopt/plot.py
```

The naive and tuned rungs dominate the runtime (~1.2 s each); the algorithmic rungs are milliseconds.

## 5 Whys

1. **Why did genuine tuning give no speedup at all?** Because the naive loop already spends almost all
   its time inside the compiled `re` engine, leaving no Python-level overhead for line-level tweaks to
   remove.
2. **Why did the combined regex give 513x despite being one line?** Python's regex engine scans an
   alternation of literal strings in roughly a single pass, so merging K patterns into one replaces the
   O(N·K) "test every pattern" algorithm with a near-O(N) scan — an algorithmic change wearing a
   one-liner's clothes.
3. **Why does explicit Aho-Corasick beat even the combined regex?** It's a purpose-built automaton for
   multi-pattern matching with a tighter scan and a cheap candidate confirmation, so it shaves the
   constant factor the general-purpose regex engine still carries.
4. **Why does Rawlinson's 2-10x / 10-100x partition mostly hold but not perfectly?** The qualitative
   split — tuning small, reframes large — held emphatically; the numeric bands are softer, because an
   already-efficient process can yield 1x to tuning and an "optimization" can secretly be a reframe.
5. **Why does the tuning-vs-reframe distinction matter for where you spend effort?** Because effort
   spent tuning an already-compiled hot path returns almost nothing, while effort spent reducing the
   *amount* of work (the algorithm) returns orders of magnitude — so the first question should be "can
   I change the algorithm?", not "can I make this loop tighter?".

**Root cause:** speedups come from doing less work, not from doing the same work more neatly. When the
work already runs in compiled code, implementation tuning has nothing to remove and returns ~1x; the
order-of-magnitude wins require an algorithmic change that cuts the work itself — and whether an edit
counts as "tuning" or "reframing" is determined by that effect, not by how small the edit looks, which
is why a single combined regex lands in the same band as a hand-built automaton.
